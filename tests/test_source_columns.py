"""Display columns preserve CR/LF and UTF-8 behavior."""

import unittest

from repository_intelligence.source import utf8_display_column


class SourceColumnTests(unittest.TestCase):
    def test_newline_first_scan_matches_full_boundary_search(self):
        for source in (b"first\nsecond\nthird", b"first\rsecond\rthird",
                       b"first\r\nsecond\nthird\rfourth",
                       "éclair\n東京\r\nlast".encode()):
            with self.subTest(source=source):
                for offset in range(len(source) + 1):
                    line_start = max(source.rfind(b"\n", 0, offset),
                                     source.rfind(b"\r", 0, offset)) + 1
                    expected = len(source[line_start:offset].decode("utf-8", "replace")) + 1
                    self.assertEqual(utf8_display_column(source, offset), expected)


if __name__ == "__main__":
    unittest.main()
