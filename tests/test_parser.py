"""解析器与模型测试：覆盖 vCard 2.1 / 3.0 / 4.0、QP 解码、折叠、转义。"""

import unittest

from vcardforge import parse_text, ParseError
from vcardforge.model import _parse_date


VCARD30 = """BEGIN:VCARD
VERSION:3.0
FN:张三
N:张;三;;;
TEL;TYPE=CELL:+86 138 0013 8000
TEL;TYPE=HOME:010-6500 1234
EMAIL;TYPE=INTERNET:zhangsan@example.com
ORG:示例科技;研发部
TITLE:工程师
BDAY:1990-02-14
END:VCARD
"""

VCARD21_QP = (
    "BEGIN:VCARD\r\n"
    "VERSION:2.1\r\n"
    "N:李;四;;;\r\n"
    "FN:=E6=9D=8E=E5=9B=9B\r\n"
    "NOTE;ENCODING=QUOTED-PRINTABLE;CHARSET=UTF-8:=E7=AC=AC=E4=B8=80=E8=A1=8C=\r\n"
    " =E7=AC=AC=E4=BA=8C=E8=A1=8C\r\n"
    "TEL;CELL:+8613900139000\r\n"
    "END:VCARD\r\n"
)

VCARD40 = """BEGIN:VCARD
VERSION:4.0
FN:王五
UID:urn:uuid:123e4567-e89b-12d3-a456-426614174000
TEL;TYPE=cell:+8618900138900
BDAY:--03-08
END:VCARD
"""

FOLDED = """BEGIN:VCARD
VERSION:3.0
FN:折叠测试
NOTE:这一行很长很长所以需要被折叠续行 下一行以空格开头合并到本行
END:VCARD
"""


class TestParser(unittest.TestCase):
    def test_basic_v30(self):
        contacts = parse_text(VCARD30)
        self.assertEqual(len(contacts), 1)
        c = contacts[0]
        self.assertEqual(c.fn, "张三")
        self.assertEqual(c.n, ("张", "三", "", "", ""))
        self.assertEqual(len(c.phones), 2)
        self.assertEqual(c.phones[0].types, ("cell",))
        self.assertEqual(c.orgs, ["示例科技;研发部"])
        self.assertEqual(c.title, "工程师")
        self.assertEqual(len(c.birthdays), 1)
        self.assertEqual(c.birthdays[0].date.year, 1990)
        self.assertEqual(c.birthdays[0].date.month, 2)
        self.assertEqual(c.birthdays[0].date.day, 14)

    def test_v21_quoted_printable(self):
        contacts = parse_text(VCARD21_QP)
        c = contacts[0]
        self.assertEqual(c.fn, "李四")
        self.assertEqual(len(c.phones), 1)
        self.assertEqual(c.phones[0].types, ("cell",))
        self.assertIn("第一行", c.note)
        self.assertIn("第二行", c.note)

    def test_v40_and_no_year_bday(self):
        c = parse_text(VCARD40)[0]
        self.assertEqual(c.version, "4.0")
        self.assertIsNotNone(c.uid)
        b = c.birthdays[0]
        self.assertEqual((b.date.month, b.date.day), (3, 8))

    def test_line_folding(self):
        c = parse_text(FOLDED)[0]
        self.assertIn("续行", c.note)
        self.assertIn("合并", c.note)

    def test_escapes_unescaped(self):
        text = (
            "BEGIN:VCARD\nVERSION:3.0\nFN:转义\\,测试\n"
            "NOTE:第一\\n第二\\;分号\nEND:VCARD\n"
        )
        c = parse_text(text)[0]
        self.assertEqual(c.fn, "转义,测试")
        self.assertIn("第一\n第二", c.note)
        self.assertIn(";分号", c.note)

    def test_multiple_cards(self):
        text = VCARD30 + VCARD40
        self.assertEqual(len(parse_text(text)), 2)

    def test_empty_text(self):
        self.assertEqual(parse_text(""), [])
        self.assertEqual(parse_text("   \n  "), [])

    def test_unclosed_raises(self):
        with self.assertRaises(ParseError):
            parse_text("BEGIN:VCARD\nVERSION:3.0\nFN:x\n")

    def test_orphan_end_raises(self):
        with self.assertRaises(ParseError):
            parse_text("END:VCARD\n")

    def test_item_prefix_stripped(self):
        text = (
            "BEGIN:VCARD\nVERSION:3.0\nFN:分组\nitem1.TEL:+8613800138000\n"
            "item1.X-ABLabel:_$!<Mobile>!$_\nEND:VCARD\n"
        )
        c = parse_text(text)[0]
        self.assertEqual(len(c.phones), 1)
        self.assertEqual(c.phones[0].raw, "+8613800138000")

    def test_garbage_line_ignored(self):
        text = "这不是vcard的行\n" + VCARD30
        self.assertEqual(len(parse_text(text)), 1)


class TestDateParse(unittest.TestCase):
    def test_formats(self):
        cases = {
            "1990-02-14": (1990, 2, 14),
            "19900214": (1990, 2, 14),
            "1990-02-14T00:00": (1990, 2, 14),
            "--03-08": (2000, 3, 8),
            "-03-08": (2000, 3, 8),
        }
        for raw, expected in cases.items():
            d = _parse_date(raw)
            self.assertIsNotNone(d, raw)
            self.assertEqual((d.year, d.month, d.day), expected, raw)

    def test_invalid(self):
        self.assertIsNone(_parse_date("not-a-date"))
        self.assertIsNone(_parse_date(""))


class TestBirthdayNext(unittest.TestCase):
    def test_days_until_next(self):
        import datetime

        from vcardforge.model import Birthday

        b = Birthday(kind="bday", raw="1990-02-14", date=datetime.date(1990, 2, 14))
        today = datetime.date(2026, 2, 10)
        self.assertEqual(b.days_until_next(today), 4)
        # 已过的生日 -> 下一年
        self.assertEqual(b.days_until_next(datetime.date(2026, 3, 1)), 350)

    def test_feb29_fallback(self):
        import datetime

        from vcardforge.model import Birthday

        b = Birthday(kind="bday", raw="2000-02-29", date=datetime.date(2000, 2, 29))
        today = datetime.date(2026, 2, 27)
        # 2026 不是闰年 -> 回退到 2/28
        self.assertEqual(b.days_until_next(today), 1)


if __name__ == "__main__":
    unittest.main()
