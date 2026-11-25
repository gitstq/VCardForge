"""vCard 文本解析器：支持 vCard 2.1 / 3.0 / 4.0。

自研实现要点（不依赖任何第三方库）:

    1. **行折叠还原（unfold）**：vCard 规定长行以 CRLF + 空白（2.1/3.0）
       或 CRLF 后紧跟空格/制表符（4.0）续行，先统一还原为逻辑行；
    2. **参数解析**：``TEL;TYPE=CELL;TYPE=VOICE:...`` 与 2.1 的简写
       ``TEL;CELL;VOICE:...``（裸参数视为 TYPE）都能正确归位；
    3. **QUOTED-PRINTABLE 解码**：vCard 2.1 中 NOTE 等字段常用
       ``ENCODING=QUOTED-PRINTABLE`` + ``CHARSET=UTF-8``，且 ``=`` 换行
       软折叠需与物理折叠一起处理；
    4. **分组前缀**：Outlook 等导出的 ``item1.TEL`` 前缀会被剥离；
    5. **非破坏性**：未识别的属性原样保留，保证往返无损。

仅使用 Python 标准库。
"""

from __future__ import annotations

import base64
import quopri
import re
from typing import Dict, List, Tuple

from .model import Contact

__all__ = ["parse_text", "parse_file", "ParseError", "unfold_lines"]


class ParseError(ValueError):
    """vCard 文本结构损坏时抛出。"""


Property = Tuple[str, Dict[str, List], str]


def parse_file(path: str, encoding: str = "utf-8") -> List[Contact]:
    """从文件读取并解析 .vcf 文本，返回联系人列表。"""
    with open(path, "r", encoding=encoding, errors="replace") as fh:
        return parse_text(fh.read())


def parse_text(text: str) -> List[Contact]:
    """解析 vCard 文本 -> ``List[Contact]``。

    自动容忍:
        - CRLF / LF 混合换行
        - UTF-8 BOM
        - vCard 外的前后空白
    """
    text = text.lstrip("\ufeff")
    if not text.strip():
        return []
    logical = unfold_lines(text)
    # BEGIN/END 配对切分
    cards: List[List[str]] = []
    current: List[str] = []
    inside = False
    for line in logical:
        upper = line.strip().upper()
        if upper == "BEGIN:VCARD":
            if inside:
                raise ParseError("嵌套的 BEGIN:VCARD（上一个卡片未以 END:VCARD 结束）")
            inside = True
            current = []
        elif upper == "END:VCARD":
            if not inside:
                raise ParseError("孤立的 END:VCARD（缺少 BEGIN:VCARD）")
            cards.append(current)
            current = []
            inside = False
        elif inside:
            current.append(line)
    if inside:
        raise ParseError("vCard 未闭合：缺少 END:VCARD")

    contacts: List[Contact] = []
    for body in cards:
        contacts.append(_parse_card(body))
    return contacts


# ----------------------------------------------------------------------
# 行折叠还原
# ----------------------------------------------------------------------
def unfold_lines(text: str) -> List[str]:
    """把物理行还原为逻辑行。

    规则:
        - 换行 + 空格/制表符开头 -> 折叠续行（vCard 2.1/3.0/4.0）；
        - QUOTED-PRINTABLE 的 ``=`` 行尾软折叠在解码阶段处理。
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    out: List[str] = []
    for phys in text.split("\n"):
        if phys[:1] in (" ", "\t") and out:
            out[-1] += phys[1:]
        else:
            out.append(phys)
    # 丢掉纯空白行
    return [ln for ln in out if ln.strip()]


# ----------------------------------------------------------------------
# 单卡解析
# ----------------------------------------------------------------------
_PROP_RE = re.compile(r"(?P<name>[^:;]*)(?P<params>(?:;[^:]*)*):(?P<value>.*)", re.S)


def _parse_card(body: List[str]) -> Contact:
    props: List[Property] = []
    for line in body:
        prop = _parse_property(line)
        if prop is not None:
            props.extend(prop)
    return Contact(properties=props)


def _parse_property(line: str) -> List[Property]:
    """解析单个逻辑行 -> ``[(name, params, value), ...]``。

    返回列表是因为一个 QUOTED-PRINTABLE 属性解码后可能产生多行
    （如换行的 NOTE），写入时会成为多个连续同名属性。
    """
    m = _PROP_RE.match(line)
    if not m:
        return []  # 无法识别的行：静默跳过而不是让整个文件报废
    raw_name = m.group("name").strip()
    params_part = m.group("params") or ""
    value = m.group("value")

    # 分离分组前缀 item1.TEL -> TEL
    name = raw_name
    if "." in name:
        head, tail = name.split(".", 1)
        if head.lower().startswith("item") and tail:
            name = tail

    # 解析参数
    params: Dict[str, List] = {}
    for chunk in _split_params(params_part):
        if not chunk:
            continue
        if "=" in chunk:
            key, _, val = chunk.partition("=")
            key = key.strip().upper()
            val = val.strip().strip('"')
            vals = [v.strip().strip('"') for v in val.split(",") if v.strip()]
            params.setdefault(key, []).extend(vals)
        else:
            # vCard 2.1 简写：裸 token 一律当作 TYPE
            params.setdefault("TYPE", []).append(chunk.strip())

    # 解码
    values = _decode_value(name, params, value)
    return [(name, params, v) for v in values]


def _split_params(params_part: str) -> List[str]:
    """按分号切参数，但忽略 BASE64 值里不可能出现在参数区的分号。

    参数区一定在第一个冒号之前（_PROP_RE 已保证），因此直接切分即可。
    """
    if not params_part:
        return []
    return [p for p in params_part.lstrip(";").split(";")]


def _decode_value(name: str, params: Dict[str, List], value: str) -> List[str]:
    """根据 ENCODING / CHARSET 解码属性值。

    返回值列表：QUOTED-PRINTABLE 解码后按换行拆分为多条；其余为单条。
    """
    enc = ""
    for e in params.get("ENCODING", []):
        enc = e.lower()
    charset = "utf-8"
    for c in params.get("CHARSET", []):
        charset = c or "utf-8"

    if enc in ("quoted-printable", "qp"):
        raw = value
        # 行尾软折叠 "=" 与下一行续行连接后形成的 "==XX" 边界 -> 还原为 "=XX"
        raw = re.sub(r"=(?==)", "", raw)
        # 去掉行尾软折叠标记 =\n（unfold 已合并物理行，仅残留 = 结尾）
        if raw.endswith("="):
            raw = raw[:-1]
        try:
            decoded = quopri.decodestring(raw.encode("latin-1", "replace"))
            text = decoded.decode(charset, errors="replace")
        except (LookupError, ValueError):
            text = quopri.decodestring(raw.encode("latin-1", "replace")).decode(
                "utf-8", errors="replace"
            )
        return [seg for seg in text.split("\n") if seg.strip()]

    if enc in ("base64", "b"):
        try:
            base64.b64decode(value, validate=False)
        except (ValueError, TypeError):
            pass  # 解不开也原样保留，不丢数据
        return [value]

    # 无编码声明时的启发式：整段值都是 QP 序列（=XX 形式）-> 按 QP 解码。
    # 常见于损坏的 vCard 2.1 导出（FN 等字段漏写 ENCODING 参数）。
    if not enc and re.fullmatch(r"(?:=[0-9A-Fa-f]{2})+", value.strip()):
        params.setdefault("ENCODING", []).append("QUOTED-PRINTABLE")
        return _decode_value(name, params, value)

    # 无编码：对 2.1 的 CHARSET 但值实际为转义文本的情况统一做反转义
    return [_unescape(value)]


def _unescape(value: str) -> str:
    """反转义 vCard 文本值（\\n \\N \\, \\; \\\\）。

    按规范，反斜杠后的字符如果是 n/N/,/; 都有特殊含义，
    其余情况保留原字符并丢掉多余的反斜杠。
    """
    out = []
    i = 0
    n = len(value)
    while i < n:
        ch = value[i]
        if ch == "\\" and i + 1 < n:
            nxt = value[i + 1]
            if nxt in ("n", "N"):
                out.append("\n")
                i += 2
                continue
            if nxt in (",", ";", "\\"):
                out.append(nxt)
                i += 2
                continue
            out.append(nxt)
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)
