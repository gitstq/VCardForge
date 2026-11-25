"""多文件合并与智能去重引擎。

去重策略（自研加权评分，无需任何外部服务）::

    信号                权重
    ------------------  ----
    规范化手机号相同     0.60
    邮箱相同             0.30
    姓名完全相同         0.10
    评分 >= 0.60 视为同一人

    即「手机号相同」单信号即可判定；「邮箱相同 + 姓名相同」也可判定；
    仅姓名相同不合并（同名不同人太常见）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Dict, Iterable, List, Optional, Tuple

from .model import Contact
from .phone import phone_key, normalize_phone

__all__ = ["merge_contacts", "dedup_contacts", "MergeReport"]

_PHONE_WEIGHT = 0.60
_EMAIL_WEIGHT = 0.30
_NAME_WEIGHT = 0.10
_THRESHOLD = 0.60


@dataclass
class MergeReport:
    """合并/去重结果报告。"""

    kept: List[Contact] = field(default_factory=list)
    """保留下的联系人（已按序去重）。"""

    merged_pairs: List[Tuple[int, int]] = field(default_factory=list)
    """被合并掉的 (保留者原索引, 丢弃者原索引) 对。"""

    @property
    def removed_count(self) -> int:
        return len(self.merged_pairs)


def merge_contacts(*sources: List[Contact]) -> Tuple[List[Contact], MergeReport]:
    """合并多个联系人列表并去重。

    用法::

        merged, report = merge_contacts(list_a, list_b, list_c)
    """
    all_contacts: List[Contact] = []
    for src in sources:
        all_contacts.extend(src)
    return dedup_contacts(all_contacts)


def dedup_contacts(contacts: List[Contact]) -> Tuple[List[Contact], MergeReport]:
    """对单个列表去重（保持原有顺序，每组重复保留信息最完整的一条）。"""
    report = MergeReport()
    if not contacts:
        return [], report

    # 预计算信号
    phones_list: List[List[str]] = []
    emails_list: List[List[str]] = []
    names_list: List[str] = []
    for c in contacts:
        phones_list.append([phone_key(p.raw) for p in c.phones if phone_key(p.raw)])
        emails_list.append([e.key() for e in c.emails if e.key()])
        names_list.append(_norm_name(c.display_name))

    # 并查集做传递性合并（A~B 且 B~C => A,B,C 同组）
    parent = list(range(len(contacts)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    # 手机号倒排索引：同号 -> 候选对（避免 O(n^2) 全比对）
    by_phone: Dict[str, List[int]] = {}
    for i, phones in enumerate(phones_list):
        for p in phones:
            by_phone.setdefault(p, []).append(i)
    for idxs in by_phone.values():
        for i in idxs[1:]:
            union(idxs[0], i)

    # 剩余候选对：共享邮箱或高相似姓名
    by_email: Dict[str, List[int]] = {}
    for i, emails in enumerate(emails_list):
        for e in emails:
            by_email.setdefault(e, []).append(i)
    for idxs in by_email.values():
        for i in idxs[1:]:
            union(idxs[0], i)

    # 姓名相同（含模糊相似 >=0.85）的候选对，需要综合评分确认
    seen_pairs = set()
    n = len(contacts)
    for i in range(n):
        for j in range(i + 1, n):
            if find(i) == find(j):
                continue
            pair = (i, j)
            if pair in seen_pairs:
                continue
            score = _similarity(i, j, phones_list, emails_list, names_list)
            if score >= _THRESHOLD:
                union(i, j)
            seen_pairs.add(pair)

    # 分组：组内选信息最完整的做代表
    groups: Dict[int, List[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)

    kept: List[Contact] = []
    for root in sorted(groups):
        idxs = groups[root]
        best = max(idxs, key=lambda i: _completeness(contacts[i]))
        kept.append(contacts[best])
        for idx in idxs:
            if idx != best:
                report.merged_pairs.append((best, idx))
    report.merged_pairs.sort()
    report.kept = kept
    return kept, report


def _norm_name(name: str) -> str:
    return "".join((name or "").split()).lower()


def _similarity(
    i: int,
    j: int,
    phones_list: List[List[str]],
    emails_list: List[List[str]],
    names_list: List[str],
) -> float:
    """加权综合评分。"""
    score = 0.0
    if set(phones_list[i]) & set(phones_list[j]):
        score += _PHONE_WEIGHT
    if set(emails_list[i]) & set(emails_list[j]):
        score += _EMAIL_WEIGHT
    ni, nj = names_list[i], names_list[j]
    if ni and nj and ni == nj:
        score += _NAME_WEIGHT
    elif ni and nj and len(ni) >= 3 and len(nj) >= 3:
        if SequenceMatcher(None, ni, nj).ratio() >= 0.85:
            score += _NAME_WEIGHT
    return score


def _completeness(contact: Contact) -> int:
    """信息完整度：字段越多越优先保留。"""
    score = 0
    if contact.fn:
        score += 2
    if contact.n and any(contact.n):
        score += 2
    score += min(len(contact.phones), 3)
    score += min(len(contact.emails), 2)
    if contact.orgs:
        score += 1
    if contact.note:
        score += 1
    if contact.birthdays:
        score += 1
    if contact.uid:
        score += 1
    return score
