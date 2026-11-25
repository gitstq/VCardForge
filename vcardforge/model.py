"""数据模型：通讯录联系人的结构化表示。

设计要点:
    - ``Contact`` 保存原始属性列表（保留解析时的一切信息），同时提供
      FN / N / TEL / EMAIL / BDAY / ORG 等常用字段的快捷访问器；
    - 所有快捷访问器均为惰性视图，不改动原始属性，保证「解析 -> 输出」
      的往返（round-trip）不丢数据；
    - ``PhoneNumber`` / ``EmailAddress`` / ``Birthday`` 为轻量值对象。
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class PhoneNumber:
    """一个 TEL 属性：号码原文 + 规范化结果 + 可选类型标签。"""

    raw: str
    """用户输入的原始号码，如 ``+86 138 0013 8000``。"""

    normalized: str = ""
    """规范化后的号码（E.164 风格，如 ``+8613800138000``）。"""

    types: Tuple[str, ...] = ()
    """vCard 类型参数，如 ``("cell", "voice")``。"""

    def key(self) -> str:
        """用于去重比较的键：优先规范化号码，其次去除非数字后的原文。"""
        return self.normalized or "".join(ch for ch in self.raw if ch.isdigit())

    def __str__(self) -> str:  # pragma: no cover - 仅为调试便利
        return self.raw


@dataclass
class EmailAddress:
    """一个 EMAIL 属性：地址 + 可选类型标签。"""

    value: str
    types: Tuple[str, ...] = ()

    def key(self) -> str:
        return self.value.strip().lower()


@dataclass
class Birthday:
    """BDAY / ANNIVERSARY 属性。

    ``kind`` 为 ``"bday"``（生日）或 ``"anniversary"``（纪念日）。
    ``date`` 无法解析时为 ``None``，此时保留 ``raw`` 文本供输出。
    """

    kind: str
    raw: str
    date: Optional[datetime.date] = None

    def days_until_next(self, today: Optional[datetime.date] = None) -> Optional[int]:
        """距离下一次生日/纪念日的天数（含闰年 2 月 29 日回退到 2 月 28 日的处理）。"""
        if self.date is None:
            return None
        today = today or datetime.date.today()
        try:
            nxt = self.date.replace(year=today.year)
        except ValueError:
            # 2 月 29 日在平年不存在 -> 回退到 2 月 28 日
            nxt = self.date.replace(year=today.year, day=28)
        if nxt < today:
            try:
                nxt = self.date.replace(year=today.year + 1)
            except ValueError:
                nxt = self.date.replace(year=today.year + 1, day=28)
        return (nxt - today).days


@dataclass
class Contact:
    """单个联系人。

    ``properties`` 是 ``(name, params, value)`` 三元组列表，其中
    ``params`` 是 ``{参数名: [值, ...]}`` 字典；这是解析器的原始输出，
    也是写入器的输入，保证 round-trip 无损。
    """

    properties: List[Tuple[str, dict, str]] = field(default_factory=list)

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    def _props(self, name: str) -> List[Tuple[str, dict, str]]:
        want = name.upper()
        out = []
        for pname, params, value in self.properties:
            base = pname.split(".", 1)[-1].upper()  # 去掉 item1. 分组前缀
            if base == want:
                out.append((pname, params, value))
        return out

    def _first(self, name: str) -> Optional[str]:
        props = self._props(name)
        return props[0][2] if props else None

    # ------------------------------------------------------------------
    # 快捷访问器
    # ------------------------------------------------------------------
    @property
    def fn(self) -> Optional[str]:
        """FN（显示名）。"""
        return self._first("FN")

    @property
    def n(self) -> Optional[Tuple[str, str, str, str, str]]:
        """N（结构化姓名）：返回 (姓, 名, 中间名, 前缀, 后缀)。"""
        v = self._first("N")
        if v is None:
            return None
        parts = v.split(";")
        parts += [""] * (5 - len(parts))
        return tuple(p.strip() for p in parts[:5])

    @property
    def display_name(self) -> str:
        """最佳可用显示名：FN > 姓+名 > 昵称 > ORG > ``"(未命名)"``。"""
        if self.fn:
            return self.fn
        n = self.n
        if n:
            joined = "".join(part for part in (n[0], n[1]) if part)
            if joined:
                return joined
        nick = self._first("NICKNAME")
        if nick:
            return nick
        orgs = self.orgs
        if orgs:
            return orgs[0]
        return "(未命名)"

    @property
    def orgs(self) -> List[str]:
        return [v for _, _, v in self._props("ORG")]

    @property
    def title(self) -> Optional[str]:
        return self._first("TITLE")

    @property
    def note(self) -> Optional[str]:
        return self._first("NOTE")

    @property
    def uid(self) -> Optional[str]:
        return self._first("UID")

    @property
    def version(self) -> str:
        v = self._first("VERSION")
        return v or "3.0"

    # ------------------------------------------------------------------
    # 电话 / 邮箱 / 生日
    # ------------------------------------------------------------------
    @property
    def phones(self) -> List[PhoneNumber]:
        out: List[PhoneNumber] = []
        for _, params, value in self._props("TEL"):
            types = tuple(
                t.lower()
                for vals in params.get("TYPE", [])
                for t in (vals if isinstance(vals, list) else [vals])
                if isinstance(vals, str)
            )
            out.append(PhoneNumber(raw=value, types=types))
        return out

    @property
    def emails(self) -> List[EmailAddress]:
        out: List[EmailAddress] = []
        for _, params, value in self._props("EMAIL"):
            types = tuple(
                t.lower()
                for vals in params.get("TYPE", [])
                for t in (vals if isinstance(vals, list) else [vals])
                if isinstance(vals, str)
            )
            out.append(EmailAddress(value=value, types=types))
        return out

    @property
    def birthdays(self) -> List[Birthday]:
        out: List[Birthday] = []
        for name, _, value in self._props("BDAY") + self._props("ANNIVERSARY"):
            kind = "bday" if name.split(".")[-1].upper() == "BDAY" else "anniversary"
            out.append(Birthday(kind=kind, raw=value, date=_parse_date(value)))
        return out

    @property
    def addresses(self) -> List[str]:
        """ADR 属性的紧凑文本表示。"""
        out = []
        for _, _, v in self._props("ADR"):
            segs = [s.strip() for s in v.split(";") if s.strip()]
            out.append(" ".join(segs))
        return out


def _parse_date(text: str) -> Optional[datetime.date]:
    """解析 vCard 日期文本（支持 YYYY-MM-DD / YYYYMMDD / 含时间部分）。

    兼容 ``--0214``（无年份）与 ``1980-02-14T00:00`` 等变体。
    """
    text = text.strip().strip('"')
    if not text:
        return None
    # 截掉时间部分
    head = text.split("T")[0].split("t")[0]
    # --MM-DD / -MM-DD（vCard 4.0 允许省略年份）-> 用 2000 作占位年
    if head.startswith("-"):
        head = "2000-" + head.lstrip("-")
    head = head.rstrip("Zz")
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y-%m", "%Y"):
        try:
            d = datetime.datetime.strptime(head, fmt).date()
            return d
        except ValueError:
            continue
    return None
