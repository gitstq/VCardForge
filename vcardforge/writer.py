"""vCard 写入器：生成 vCard 3.0 或 4.0 文本。

特性:
    - 按规范进行行折叠（每行不超过 75 字节，续行以空格开头）；
    - 值转义（逗号 / 分号 / 反斜杠 / 换行）；
    - 参数以 ``TYPE=...`` 形式输出（4.0 同样兼容）；
    - 自动补全 VERSION / FN / N 必需属性，确保输出可被主流通讯录
      （iOS / Android / Outlook）导入。
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from .model import Contact

__all__ = ["write_text", "write_file"]


def write_file(contacts: Iterable[Contact], path: str, version: str = "3.0") -> None:
    """把联系人列表写为 .vcf 文件。"""
    with open(path, "w", encoding="utf-8", newline="\r\n") as fh:
        fh.write(write_text(contacts, version=version))


def write_text(contacts: Iterable[Contact], version: str = "3.0") -> str:
    """把联系人列表序列化为 vCard 文本。"""
    if version not in ("3.0", "4.0"):
        raise ValueError(f"不支持的输出版本：{version}（仅支持 3.0 / 4.0）")
    lines: List[str] = []
    for contact in contacts:
        lines.extend(_write_card(contact, version))
    return "\r\n".join(lines) + ("\r\n" if lines else "")


_ESCAPES = {
    "\\": "\\\\",
    ";": "\\;",
    ",": "\\,",
    "\n": "\\n",
}


def _escape(value: str) -> str:
    for old, new in _ESCAPES.items():
        value = value.replace(old, new)
    return value


def _fold(line: str) -> List[str]:
    """按 RFC 规范折叠：每行最多 75 字节（UTF-8），续行以空格开头。"""
    encoded = line.encode("utf-8")
    if len(encoded) <= 75:
        return [line]
    out: List[str] = []
    limit = 75
    current = ""
    current_bytes = 0
    for ch in line:
        ch_bytes = len(ch.encode("utf-8"))
        if current_bytes + ch_bytes > limit:
            out.append(current)
            current = " " + ch
            current_bytes = 1 + ch_bytes
            limit = 75
        else:
            current += ch
            current_bytes += ch_bytes
    if current:
        out.append(current)
    return out


def _write_card(contact: Contact, version: str) -> List[str]:
    lines: List[str] = ["BEGIN:VCARD", f"VERSION:{version}"]

    fn = contact.fn or contact.display_name
    lines.append(f"FN:{_escape(fn)}")

    n = contact.n
    if not n or not any(n):
        # 从 FN 猜测结构化姓名：西式 "Given Family"，中文按原样放姓位
        guess = contact.fn or ""
        if guess and " " in guess:
            first, _, last = guess.partition(" ")
            n = (last, first, "", "", "")
        else:
            n = (guess, "", "", "", "")
    lines.append("N:" + ";".join(_escape(p) for p in n))

    uid = contact.uid
    if not uid:
        import uuid

        uid = str(uuid.uuid4())
    if version == "4.0" or contact.uid:
        lines.append(f"UID:{_escape(uid)}")

    skip = {"BEGIN", "END", "VERSION", "FN", "N"}
    for name, params, value in contact.properties:
        base = name.split(".", 1)[-1].upper()
        if base in skip:
            continue
        prop = name if "." in name else base
        param_str = ""
        types = [t for t in params.get("TYPE", []) if isinstance(t, str) and t]
        if types and base not in ("NOTE", "UID"):
            param_str = ";TYPE=" + ",".join(t.upper() for t in types)
        lines.append(f"{prop}{param_str}:{_escape(value)}")
    lines.append("END:VCARD")
    # 按 RFC 折叠超长行
    folded: List[str] = []
    for line in lines:
        folded.extend(_fold(line))
    return folded
