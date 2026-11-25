"""写入器 round-trip、电话规范化、合并去重、导出、校验测试。"""

import csv
import io
import json
import os
import tempfile
import unittest

from vcardforge import (
    Contact,
    dedup_contacts,
    merge_contacts,
    normalize_phone,
    parse_text,
    to_csv,
    to_json,
    validate_contacts,
    write_file,
    write_text,
)


def _make(fn, tel="", email=""):
    lines = ["BEGIN:VCARD", "VERSION:3.0", f"FN:{fn}", f"N:{fn};"]
    if tel:
        lines.append(f"TEL;TYPE=CELL:{tel}")
    if email:
        lines.append(f"EMAIL:{email}")
    lines.append("END:VCARD")
    return parse_text("\n".join(lines))[0]


class TestWriter(unittest.TestCase):
    def test_round_trip(self):
        src = """BEGIN:VCARD
VERSION:3.0
FN:测试人
N:测;试;;;
TEL;TYPE=CELL:+8613800138000
EMAIL:test@example.com
ORG:某公司
NOTE:备注内容
END:VCARD
"""
        c = parse_text(src)[0]
        out = write_text([c], version="3.0")
        c2 = parse_text(out)[0]
        self.assertEqual(c2.fn, "测试人")
        self.assertEqual(c2.n, ("测", "试", "", "", ""))
        self.assertEqual(c2.phones[0].raw, "+8613800138000")
        self.assertEqual(c2.emails[0].value, "test@example.com")
        self.assertEqual(c2.orgs, ["某公司"])
        self.assertEqual(c2.note, "备注内容")

    def test_version4_output(self):
        c = _make("甲", tel="13800138000")
        out = write_text([c], version="4.0")
        c2 = parse_text(out)[0]
        self.assertEqual(c2.version, "4.0")
        self.assertTrue(c2.uid)

    def test_invalid_version_rejected(self):
        with self.assertRaises(ValueError):
            write_text([], version="2.1")

    def test_escapes_on_write(self):
        c = parse_text("BEGIN:VCARD\nVERSION:3.0\nFN:a\nNOTE:分号;逗号,反斜杠\\换行\nEND:VCARD")[0]
        out = write_text([c])
        self.assertIn("分号\\;", out)
        self.assertIn("逗号\\,", out)
        c2 = parse_text(out)[0]
        self.assertEqual(c2.note, "分号;逗号,反斜杠换行")

    def test_folding_limit(self):
        c = parse_text(
            "BEGIN:VCARD\nVERSION:3.0\nFN:长\nNOTE:" + "长" * 80 + "\nEND:VCARD"
        )[0]
        out = write_text([c])
        for line in out.split("\r\n"):
            self.assertLessEqual(len(line.encode("utf-8")), 75, line)

    def test_write_file(self):
        c = _make("文件", tel="13900139000")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.vcf")
            write_file([c], path, version="4.0")
            with open(path, "rb") as fh:
                raw = fh.read()
            self.assertIn(b"VERSION:4.0", raw)
            self.assertIn(b"\r\n", raw)  # CRLF 换行
            # 可再次解析
            from vcardforge import parse_file

            self.assertEqual(parse_file(path)[0].fn, "文件")


class TestPhone(unittest.TestCase):
    def test_normalize(self):
        cases = {
            "+86 138 0013 8000": "+8613800138000",
            "13800138000": "+8613800138000",
            "0086 139-0013-9000": "+8613900139000",
            "010-65001234": "+8601065001234",
            "(021) 6555-8888": "+8602165558888",
            "10086": "10086",
            "+1 (415) 555-2671": "+14155552671",
        }
        for raw, expected in cases.items():
            self.assertEqual(normalize_phone(raw), expected, raw)

    def test_fullwidth(self):
        self.assertEqual(normalize_phone("１３８００１３８０００"), "+8613800138000")

    def test_empty(self):
        self.assertEqual(normalize_phone(""), "")
        self.assertEqual(normalize_phone("   "), "")


class TestMergeDedup(unittest.TestCase):
    def test_same_phone_merges(self):
        a = _make("张三", tel="13800138000", email="a@x.com")
        b = _make("张三丰", tel="138-0013-8000")
        kept, report = dedup_contacts([a, b])
        self.assertEqual(len(kept), 1)
        self.assertEqual(report.removed_count, 1)

    def test_email_plus_name_merges(self):
        a = _make("李四", email="lisi@x.com")
        b = _make("李四", email="LISI@x.com")
        kept, report = dedup_contacts([a, b])
        self.assertEqual(len(kept), 1)

    def test_same_name_only_kept(self):
        a = _make("王五", tel="13800138001")
        b = _make("王五", tel="13900139001")
        kept, report = dedup_contacts([a, b])
        self.assertEqual(len(kept), 2)

    def test_transitive_merge(self):
        a = _make("A", tel="13800138000")
        b = _make("B", tel="13800138000", email="b@x.com")
        c = _make("C", email="b@x.com")
        kept, _ = dedup_contacts([a, b, c])
        self.assertEqual(len(kept), 1)

    def test_merge_contacts_multi_source(self):
        list1 = [_make("甲", tel="13800138000")]
        list2 = [_make("甲乙", tel="+86 138 0013 8000"), _make("乙", tel="13900139000")]
        kept, report = merge_contacts(list1, list2)
        self.assertEqual(len(kept), 2)
        self.assertEqual(report.removed_count, 1)

    def test_keep_most_complete(self):
        a = _make("只有名字", tel="13800138000")
        b = _make("完整的人", tel="13800138000", email="full@x.com")
        kept, _ = dedup_contacts([a, b])
        self.assertEqual(kept[0].fn, "完整的人")

    def test_empty(self):
        kept, report = dedup_contacts([])
        self.assertEqual(kept, [])
        self.assertEqual(report.removed_count, 0)


class TestExport(unittest.TestCase):
    def test_json(self):
        c = _make("导出", tel="13800138000", email="e@x.com")
        data = json.loads(to_json([c]))
        self.assertEqual(data[0]["display_name"], "导出")
        self.assertEqual(data[0]["phones"][0]["normalized"], "+8613800138000")

    def test_csv(self):
        c = _make("表格", tel="13800138000")
        rows = list(csv.reader(io.StringIO(to_csv([c]))))
        self.assertEqual(rows[0][0], "显示名")
        self.assertEqual(rows[1][0], "表格")
        self.assertEqual(rows[1][5], "13800138000")


class TestValidate(unittest.TestCase):
    def test_clean_file(self):
        c = _make("干净", tel="13800138000", email="ok@x.com")
        report = validate_contacts([c])
        self.assertTrue(report.ok)
        self.assertEqual(report.warning_count, 0)

    def test_missing_fn_n(self):
        c = parse_text("BEGIN:VCARD\nVERSION:3.0\nTEL:13800138000\nEND:VCARD")[0]
        report = validate_contacts([c])
        self.assertFalse(report.ok)
        rules = {i.rule for i in report.issues}
        self.assertIn("R03", rules)

    def test_bad_bday_and_email(self):
        c = parse_text(
            "BEGIN:VCARD\nVERSION:3.0\nFN:坏\nBDAY:不存在的日期\nEMAIL:没有at\nEND:VCARD"
        )[0]
        report = validate_contacts([c])
        rules = {i.rule for i in report.issues}
        self.assertIn("R06", rules)
        self.assertIn("R10", rules)

    def test_cross_contact_duplicate_phone(self):
        a = _make("甲", tel="13800138000")
        b = _make("乙", tel="13800138000")
        report = validate_contacts([a, b])
        rules = {i.rule for i in report.issues}
        self.assertIn("R09", rules)

    def test_summary_text(self):
        c = _make("摘要")
        report = validate_contacts([c])
        text = report.summary()
        self.assertIn("1 个联系人", text)


if __name__ == "__main__":
    unittest.main()
