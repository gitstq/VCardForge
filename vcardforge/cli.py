"""命令行入口：``vcardforge`` / ``python -m vcardforge``。

子命令::

    info      查看文件概览（人数、版本分布、字段统计）
    validate  合规校验（10 条规则，可 CI 门禁）
    merge     合并多个 .vcf 并智能去重
    export    导出 JSON / CSV
    birthdays 未来 N 天内的生日提醒
    convert   版本转换（2.1/3.0 -> 3.0/4.0）

所有子命令零网络请求、零第三方依赖。
"""

from __future__ import annotations

import argparse
import datetime
import sys
from typing import List

from . import __version__
from .export import export_csv_file, export_json_file
from .merge import dedup_contacts
from .model import Contact
from .parser import ParseError, parse_file
from .phone import normalize_phone
from .validate import validate_contacts
from .writer import write_file

__all__ = ["main"]


def _load(paths: List[str]) -> List[Contact]:
    contacts: List[Contact] = []
    for path in paths:
        contacts.extend(parse_file(path))
    return contacts


def _cmd_info(args) -> int:
    contacts = _load(args.files)
    if not contacts:
        print("未找到任何联系人")
        return 1
    versions: dict = {}
    with_phone = with_email = with_bday = 0
    for c in contacts:
        versions[c.version] = versions.get(c.version, 0) + 1
        if c.phones:
            with_phone += 1
        if c.emails:
            with_email += 1
        if c.birthdays:
            with_bday += 1
    print(f"文件数      : {len(args.files)}")
    print(f"联系人总数  : {len(contacts)}")
    print(f"版本分布    : {versions}")
    print(f"含电话      : {with_phone}")
    print(f"含邮箱      : {with_email}")
    print(f"含生日      : {with_bday}")
    print()
    for c in contacts[: args.limit]:
        tel = c.phones[0].raw if c.phones else "-"
        print(f"  {c.display_name:<20s} {tel}")
    if len(contacts) > args.limit:
        print(f"  ... 共 {len(contacts)} 条（--limit 可调整）")
    return 0


def _cmd_validate(args) -> int:
    contacts = _load(args.files)
    report = validate_contacts(contacts)
    print(report.summary())
    if args.detail:
        for line in report.detail():
            print(line)
    return 0 if report.ok else 2


def _cmd_merge(args) -> int:
    contacts = _load(args.files)
    kept, report = dedup_contacts(contacts)
    print(f"输入 {len(contacts)} 条 -> 合并去重后 {len(kept)} 条（移除 {report.removed_count} 条重复）")
    if args.verbose:
        for a, b in report.merged_pairs[: args.limit]:
            na = contacts[a].display_name
            nb = contacts[b].display_name
            print(f"  保留 [{a}] {na}  <-  合并 [{b}] {nb}")
    write_file(kept, args.output, version=args.version)
    print(f"已写入 {args.output}（v{args.version}）")
    return 0


def _cmd_export(args) -> int:
    contacts = _load(args.files)
    if args.format == "json":
        export_json_file(contacts, args.output)
    else:
        export_csv_file(contacts, args.output)
    print(f"已导出 {len(contacts)} 条 -> {args.output}")
    return 0


def _cmd_birthdays(args) -> int:
    contacts = _load(args.files)
    today = datetime.date.today()
    hits = []
    for c in contacts:
        for b in c.birthdays:
            if b.kind != "bday":
                continue
            days = b.days_until_next(today)
            if days is not None and days <= args.days:
                date_str = b.date.isoformat() if b.date else b.raw
                hits.append((days, c.display_name, date_str))
    hits.sort()
    if not hits:
        print(f"未来 {args.days} 天内没有生日")
        return 0
    print(f"未来 {args.days} 天内的生日：")
    for days, name, date_str in hits:
        print(f"  {days:>4d} 天后  {name:<20s} ({date_str})")
    return 0


def _cmd_convert(args) -> int:
    contacts = _load(args.files)
    for c in contacts:
        for p in c.phones:
            p.normalized = normalize_phone(p.raw)
    write_file(contacts, args.output, version=args.version)
    print(f"{len(contacts)} 条联系人已转换为 vCard {args.version} -> {args.output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vcardforge",
        description="VCardForge - 零依赖 · 离线优先的 vCard (.vcf) 通讯录工具箱",
    )
    parser.add_argument("--version", action="version", version=f"vcardforge {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("info", help="查看文件概览")
    p.add_argument("files", nargs="+", help=".vcf 文件路径")
    p.add_argument("--limit", type=int, default=20, help="最多列出多少条联系人")
    p.set_defaults(func=_cmd_info)

    p = sub.add_parser("validate", help="合规校验（10 条规则）")
    p.add_argument("files", nargs="+")
    p.add_argument("--detail", action="store_true", help="逐条列出问题明细")
    p.set_defaults(func=_cmd_validate)

    p = sub.add_parser("merge", help="合并多个 .vcf 并智能去重")
    p.add_argument("files", nargs="+")
    p.add_argument("-o", "--output", required=True, help="输出文件路径")
    p.add_argument("--version", default="3.0", choices=["3.0", "4.0"], help="输出 vCard 版本")
    p.add_argument("-v", "--verbose", action="store_true", help="显示合并明细")
    p.add_argument("--limit", type=int, default=20, help="最多显示多少条合并明细")
    p.set_defaults(func=_cmd_merge)

    p = sub.add_parser("export", help="导出 JSON / CSV")
    p.add_argument("files", nargs="+")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--format", default="csv", choices=["csv", "json"])
    p.set_defaults(func=_cmd_export)

    p = sub.add_parser("birthdays", help="未来 N 天内的生日提醒")
    p.add_argument("files", nargs="+")
    p.add_argument("--days", type=int, default=30, help="提前多少天提醒（默认 30）")
    p.set_defaults(func=_cmd_birthdays)

    p = sub.add_parser("convert", help="vCard 版本转换（输出 3.0 / 4.0）")
    p.add_argument("files", nargs="+")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--version", default="4.0", choices=["3.0", "4.0"])
    p.set_defaults(func=_cmd_convert)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ParseError as exc:
        print(f"[解析错误] {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"[文件不存在] {exc.filename}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
