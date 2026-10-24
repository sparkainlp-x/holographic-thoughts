import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("check_page", ROOT / "scripts" / "check_page.py")
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)

GOOD = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width"><title>T</title></head>
<body><a href="#a">x</a><section id="a"><p>text</p><img src="data:image/gif;base64,AA=="></section>
<script>var x = 1;</script></body></html>"""


def run(html):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "index.html"
        p.write_text(html, encoding="utf-8")
        return cp.check_html(p)[0]


class PageChecks(unittest.TestCase):
    def test_good_page_passes(self):
        self.assertEqual(run(GOOD), [])

    def test_missing_lang_title_viewport(self):
        out = run("<!doctype html><html><head></head><body></body></html>")
        self.assertTrue(any("lang" in p for p in out))
        self.assertTrue(any("title" in p for p in out))
        self.assertTrue(any("viewport" in p for p in out))

    def test_network_resources_rejected(self):
        for bad in ('<script src="https://cdn.example/x.js"></script>',
                    '<link rel="stylesheet" href="https://cdn.example/x.css">',
                    '<img src="//cdn.example/x.png">'):
            self.assertTrue(any("network" in p for p in run(GOOD.replace("</body>", bad + "</body>"))), bad)

    def test_fetch_in_script_rejected(self):
        self.assertTrue(any("network call" in p for p in run(GOOD.replace("var x = 1;", "fetch('/a');"))))

    def test_broken_anchor_and_duplicate_id(self):
        self.assertTrue(any("no target" in p for p in run(GOOD.replace('id="a"', 'id="b"'))))
        self.assertTrue(any("duplicate" in p for p in run(GOOD.replace("<p>", '<p id="a">'))))

    def test_unbalanced_tags(self):
        self.assertTrue(run(GOOD.replace("</section>", "")))

    def test_banned_phrases_are_built_from_parts(self):
        src = (ROOT / "scripts" / "check_page.py").read_text(encoding="utf-8").lower()
        for phrase in cp.BANNED:
            self.assertNotIn(phrase, src)


class RepoChecks(unittest.TestCase):
    def test_license_metadata_wording(self):
        self.assertEqual(cp.check_license(), [])
        self.assertEqual(cp.check_metadata(), [])
        self.assertEqual(cp.check_wording(), [])

    def test_real_page_is_clean(self):
        problems, page = cp.check_html(ROOT / "index.html")
        self.assertEqual(problems, [])
        self.assertGreaterEqual(len(page.ids), 10)

    def test_main_offline_exit_code(self):
        self.assertEqual(cp.main([]), 0)


if __name__ == "__main__":
    unittest.main()
