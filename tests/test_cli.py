"""CLI 集成测试：通过 subprocess / main() 直接调用。"""

import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

from vcardforge.cli import main


SAMPLE = """BEGIN:VCARD
VERSION:3.0
FN:张三
N:张;三;;;
TEL;TYPE=CELL:13800138000
EMAIL:zhangsan@example.com
BDAY:1990-02-14
END:VCARD
BEGIN:VCARD
VERSION:2.1
N:李;四;;;
FN:李四
TEL;CELL:139-0013-9000
END:VCARD
"""


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vcf = os.path.join(self.tmp.name, "sample.vcf")
        with open(self.vcf, "w", encoding="utf-8") as fh:
            fh.write(SAMPLE)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, argv):
        buf = StringIO()
        with redirect_stdout(buf):
            code = main(argv)
        return code, buf.getvalue()

    def test_info(self):
        code, out = self._run(["info", self.vcf])
        self.assertEqual(code, 0)
        self.assertIn("联系人总数  : 2", out)
        self.assertIn("张三", out)

    def test_validate_ok(self):
        code, out = self._run(["validate", self.vcf])
        self.assertEqual(code, 0)
        self.assertIn("0 个错误", out)

    def test_merge_dedup(self):
        out_path = os.path.join(self.tmp.name, "merged.vcf")
        code, out = self._run(["merge", self.vcf, "-o", out_path, "-v"])
        self.assertEqual(code, 0)
        self.assertIn("已写入", out)
        self.assertTrue(os.path.exists(out_path))

    def test_export_json(self):
        out_path = os.path.join(self.tmp.name, "out.json")
        code, _ = self._run(["export", self.vcf, "-o", out_path, "--format", "json"])
        self.assertEqual(code, 0)
        import json

        with open(out_path, encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(len(data), 2)

    def test_export_csv(self):
        out_path = os.path.join(self.tmp.name, "out.csv")
        code, _ = self._run(["export", self.vcf, "-o", out_path, "--format", "csv"])
        self.assertEqual(code, 0)
        with open(out_path, encoding="utf-8-sig") as fh:
            head = fh.readline()
        self.assertIn("显示名", head)

    def test_birthdays(self):
        code, out = self._run(["birthdays", self.vcf, "--days", "365"])
        self.assertEqual(code, 0)
        self.assertIn("张三", out)

    def test_convert(self):
        out_path = os.path.join(self.tmp.name, "v4.vcf")
        code, _ = self._run(["convert", self.vcf, "-o", out_path, "--version", "4.0"])
        self.assertEqual(code, 0)
        with open(out_path, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("VERSION:4.0", text)

    def test_missing_file(self):
        code, _ = self._run(["info", "/nonexistent.vcf"])
        self.assertEqual(code, 1)

    def test_bad_vcf(self):
        bad = os.path.join(self.tmp.name, "bad.vcf")
        with open(bad, "w", encoding="utf-8") as fh:
            fh.write("BEGIN:VCARD\nFN:未闭合\n")
        code, _ = self._run(["info", bad])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
