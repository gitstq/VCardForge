"""JSON / CSV 导出。"""

from __future__ import annotations

import csv
import json
from io import StringIO
from typing import Iterable, List

from .model import Contact
from .phone import normalize_phone

__all__ = ["to_json", "to_csv", "export_json_file", "export_csv_file"]


def _contact_dict(contact: Contact, with_normalized: bool = True) -> dict:
    data = {
        "display_name": contact.display_name,
        "fn": contact.fn,
        "name": list(contact.n) if contact.n else None,
        "orgs": contact.orgs,
        "title": contact.title,
        "note": contact.note,
        "uid": contact.uid,
        "version": contact.version,
        "phones": [
            {
                "value": p.raw,
                "normalized": normalize_phone(p.raw) if with_normalized else None,
                "types": list(p.types),
            }
            for p in contact.phones
        ],
        "emails": [
            {"value": e.value, "types": list(e.types)} for e in contact.emails
        ],
        "birthdays": [
            {
                "kind": b.kind,
                "raw": b.raw,
                "date": b.date.isoformat() if b.date else None,
            }
            for b in contact.birthdays
        ],
        "addresses": contact.addresses,
    }
    return data


def to_json(contacts: Iterable[Contact], ensure_ascii: bool = False, indent: int = 2) -> str:
    """导出为 JSON 字符串。"""
    data = [_contact_dict(c) for c in contacts]
    return json.dumps(data, ensure_ascii=ensure_ascii, indent=indent)


def to_csv(contacts: Iterable[Contact]) -> str:
    """导出为 CSV 字符串（UTF-8，含 BOM 兼容 Excel 的变体见 ``export_csv_file``）。

    列: 显示名, 姓名, 组织, 职务, 电话1, 电话2, 电话3, 邮箱1, 邮箱2, 生日, 备注
    """
    buf = StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(
        ["显示名", "姓", "名", "组织", "职务", "电话1", "电话2", "电话3", "邮箱1", "邮箱2", "生日", "备注"]
    )
    for c in contacts:
        n = c.n or ("", "", "", "", "")
        bdays = [b.raw for b in c.birthdays if b.kind == "bday"]
        phones = [p.raw for p in c.phones]
        emails = [e.value for e in c.emails]
        phones += [""] * (3 - len(phones[:3]))
        emails += [""] * (2 - len(emails[:2]))
        writer.writerow(
            [
                c.display_name,
                n[0],
                n[1],
                ";".join(c.orgs),
                c.title or "",
                phones[0],
                phones[1],
                phones[2],
                emails[0],
                emails[1],
                bdays[0] if bdays else "",
                (c.note or "").replace("\n", " "),
            ]
        )
    return buf.getvalue()


def export_json_file(contacts: Iterable[Contact], path: str, indent: int = 2) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(to_json(contacts, indent=indent))


def export_csv_file(contacts: Iterable[Contact], path: str, excel_bom: bool = True) -> None:
    """写 CSV 文件；``excel_bom=True`` 时加 UTF-8 BOM，避免 Excel 打开乱码。"""
    text = to_csv(contacts)
    with open(path, "w", encoding="utf-8-sig" if excel_bom else "utf-8", newline="") as fh:
        fh.write(text)
