"""合规校验与质量报告。

校验规则（10 条，全部离线执行）:

    R01  缺少 FN（显示名）
    R02  缺少 N（结构化姓名）
    R03  FN 与 N 均缺失（严重：多数通讯录会拒绝导入）
    R04  缺少 VERSION
    R05  VERSION 值非法（不在 2.1/3.0/4.0）
    R06  BDAY 日期无法解析
    R07  电话号码为空或全为非数字
    R08  同一联系人内部电话重复
    R09  跨联系人电话重复（疑似同一人多条记录）
    R10  EMAIL 格式可疑（缺 @）
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List

from .model import Contact
from .phone import phone_key

__all__ = ["validate_contacts", "ValidationReport", "Issue"]

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class Issue:
    rule: str
    """规则编号，如 ``R01``。"""

    severity: str
    """``error`` / ``warning``。"""

    message: str
    contact_index: int = -1
    contact_name: str = ""


@dataclass
class ValidationReport:
    issues: List[Issue] = field(default_factory=list)
    total_contacts: int = 0

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    @property
    def ok(self) -> bool:
        return self.error_count == 0

    def summary(self) -> str:
        """人类可读的摘要文本。"""
        lines = [
            f"共 {self.total_contacts} 个联系人：{self.error_count} 个错误，{self.warning_count} 个警告",
        ]
        counter: Dict[str, int] = {}
        for issue in self.issues:
            counter[issue.rule] = counter.get(issue.rule, 0) + 1
        for rule, count in sorted(counter.items()):
            lines.append(f"  {rule} x{count}")
        return "\n".join(lines)

    def detail(self, max_lines: int = 50) -> List[str]:
        out = []
        for issue in self.issues[:max_lines]:
            who = f"[{issue.contact_index}] {issue.contact_name}" if issue.contact_index >= 0 else "-"
            out.append(f"{issue.severity.upper():7s} {issue.rule} {who}: {issue.message}")
        return out


def validate_contacts(contacts: List[Contact]) -> ValidationReport:
    """对联系人列表执行全部校验规则。"""
    report = ValidationReport(total_contacts=len(contacts))
    phone_seen: Dict[str, int] = {}
    phone_owner: Dict[str, str] = {}

    for idx, c in enumerate(contacts):
        name = c.display_name
        has_fn = bool(c.fn)
        has_n = bool(c.n and any(c.n))
        if not has_fn:
            report.issues.append(Issue("R01", "warning", "缺少 FN（显示名）", idx, name))
        if not has_n:
            report.issues.append(Issue("R02", "warning", "缺少 N（结构化姓名）", idx, name))
        if not has_fn and not has_n:
            report.issues.append(Issue("R03", "error", "FN 与 N 均缺失，多数通讯录将拒绝导入", idx, name))

        version = c.version
        if version == "3.0" and not any(
            p.split(".", 1)[-1].upper() == "VERSION" for p, _, _ in c.properties
        ):
            report.issues.append(Issue("R04", "warning", "缺少 VERSION", idx, name))
        elif version not in ("2.1", "3.0", "4.0"):
            report.issues.append(Issue("R05", "error", f"VERSION 值非法：{version!r}", idx, name))

        for b in c.birthdays:
            if b.date is None and b.raw.strip():
                report.issues.append(Issue("R06", "warning", f"生日无法解析：{b.raw!r}", idx, name))

        local_seen = set()
        for p in c.phones:
            key = phone_key(p.raw)
            if not key:
                report.issues.append(Issue("R07", "error", f"电话号码无有效数字：{p.raw!r}", idx, name))
                continue
            if key in local_seen:
                report.issues.append(Issue("R08", "warning", f"联系人内部电话重复：{p.raw}", idx, name))
            local_seen.add(key)
            if key in phone_seen:
                report.issues.append(
                    Issue(
                        "R09",
                        "warning",
                        f"电话 {p.raw} 与联系人[{phone_seen[key]}] {phone_owner[key]} 重复（疑似同一人）",
                        idx,
                        name,
                    )
                )
            else:
                phone_seen[key] = idx
                phone_owner[key] = name

        for e in c.emails:
            if e.value and not _EMAIL_RE.match(e.value.strip()):
                report.issues.append(Issue("R10", "warning", f"EMAIL 格式可疑：{e.value!r}", idx, name))

    return report
