import sys
import os
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.token_parser import TokenParser


class TestTokenParserRobustness(unittest.TestCase):

    def test_relaxed_regex_matching_sony(self):
        # Sony preset pattern expects a "C" separator: {Camera:1}{Roll:3}C{Clip:3}
        # Filename does not contain "C": A005004.MP4
        parser = TokenParser("{Camera:1}{Roll:3}C{Clip:3}")
        
        # Verify strict regex fails on A005004.MP4 but relaxed regex succeeds
        res = parser.parse("A005004.MP4")
        self.assertEqual(res["Camera"], "A")
        self.assertEqual(res["Roll"], "005")
        self.assertEqual(res["Clip"], "004")

    def test_relaxed_regex_matching_arri(self):
        # ARRI Alexa pattern expects: {Camera:1}{Roll:3}C{Clip:3}_{Date:YYMMDD}
        # Filename misses both 'C' and '_' separator, e.g. A005004260723.MP4
        parser = TokenParser("{Camera:1}{Roll:3}C{Clip:3}_{Date:YYMMDD}")
        res = parser.parse("A005004260723.MP4")
        
        self.assertEqual(res["Camera"], "A")
        self.assertEqual(res["Roll"], "005")
        self.assertEqual(res["Clip"], "004")
        self.assertEqual(res["Date"], "260723")

    def test_heuristic_fallback_standard_format(self):
        # Naming rule that is completely mismatched (e.g. expects prefix)
        # But filename is standard format A005004.MP4
        parser = TokenParser("CAM_{Project}_{Clip}")
        
        res = parser.parse("A005004.MP4")
        # Should fall back to heuristic extraction: Camera A, Roll 005
        self.assertEqual(res["Camera"], "A")
        self.assertEqual(res["Roll"], "005")

        res_b = parser.parse("B005001.MP4")
        self.assertEqual(res_b["Camera"], "B")
        self.assertEqual(res_b["Roll"], "005")


if __name__ == "__main__":
    unittest.main()
