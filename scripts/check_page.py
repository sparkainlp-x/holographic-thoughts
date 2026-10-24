#!/usr/bin/env python3
"""Static checks for the single-page site. Standard library only.

    python3 scripts/check_page.py            # offline checks
    python3 scripts/check_page.py --online   # also request the external links

Checks: the HTML parses with balanced tags; the page declares a language, a title and
a viewport; nothing is loaded from the network (no external script, stylesheet, image,
font or fetch); every in-page anchor has a target; every id is unique; the inline
script has no syntax error when node is available; LICENSE is the AGPL-3.0 text;
CITATION.cff and .zenodo.json agree on version, licence and creator; the CHANGELOG
mentions that version; and no file uses a phrase this project does not claim.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
# phrases assembled from parts so this file does not contain them literally
BANNED = [a + b for a, b in (("pro", "ven"), ("valid", "ated"), ("production", "-ready"),
                             ("quantum ", "advantage"), ("real-world ", "performance"))]
ALLOWED_NEGATION = re.compile(r"\b(not|no|never|without|neither|nor|un)\b", re.I)


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors, self.ids, self.hrefs, self.network = [], [], [], [], []
        self.title, self.lang, self.viewport, self.scripts = "", None, False, []
        self._in_title = self._in_script = False
        self._script = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "meta" and a.get("name") == "viewport":
            self.viewport = True
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "a" and "href" in a:
            self.hrefs.append(a["href"])
        for key in ("src", "srcset", "data", "poster"):
            if key in a and re.match(r"(https?:)?//", a[key] or ""):
                self.network.append(f"<{tag} {key}={a[key]}>")
        if tag == "link" and re.match(r"(https?:)?//", a.get("href") or ""):
            self.network.append(f"<link href={a['href']}>")
        if tag == "title":
            self._in_title = True
        if tag == "script" and "src" not in a:
            self._in_script = True
            self._script = []
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.stack and self.stack[-1] == tag:
            self.stack.pop()

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if tag == "title":
            self._in_title = False
        if tag == "script" and self._in_script:
            self._in_script = False
            self.scripts.append("".join(self._script))
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"unbalanced </{tag}> (open: {self.stack[-3:]})")
            if tag in self.stack:
                while self.stack and self.stack.pop() != tag:
                    pass
        else:
            self.stack.pop()

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._in_script:
            self._script.append(data)


def check_html(path):
    problems = []
    text = path.read_text(encoding="utf-8")
    p = Page()
    p.feed(text)
    p.close()
    problems += p.errors
    if p.stack:
        problems.append(f"unclosed tags: {p.stack}")
    if not p.lang:
        problems.append("html element has no lang attribute")
    if not p.title.strip():
        problems.append("page has no title")
    if not p.viewport:
        problems.append("no viewport meta tag")
    dup = sorted({i for i in p.ids if p.ids.count(i) > 1})
    if dup:
        problems.append(f"duplicate ids: {dup}")
    for h in p.hrefs:
        if h.startswith("#") and len(h) > 1 and h[1:] not in p.ids:
            problems.append(f"anchor {h} has no target")
    for n in p.network:
        problems.append(f"network resource: {n}")
    if re.search(r"\b(fetch|XMLHttpRequest|WebSocket|sendBeacon|EventSource)\s*\(", "\n".join(p.scripts)):
        problems.append("script performs a network call")
    if "https://" in "\n".join(p.scripts):
        problems.append("script contains an absolute URL")
    return problems, p


def check_js(page):
    node = shutil.which("node")
    if not node:
        return ["node not found: inline script syntax not checked (skipped)"], True
    problems = []
    for i, code in enumerate(page.scripts):
        if not code.strip():
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(code)
        r = subprocess.run([node, "--check", f.name], capture_output=True, text=True)
        Path(f.name).unlink()
        if r.returncode:
            problems.append(f"inline script {i} syntax error: {r.stderr.strip().splitlines()[-1:]}")
    return problems, False


def check_license():
    t = (ROOT / "LICENSE").read_text(encoding="utf-8")
    problems = []
    if "GNU AFFERO GENERAL PUBLIC LICENSE" not in t.upper() or "Version 3, 19 November 2007" not in t:
        problems.append("LICENSE is not the AGPL-3.0 text")
    if len(t) < 30000:
        problems.append("LICENSE looks truncated")
    return problems


def cff_value(text, key):
    m = re.search(rf"^{key}:\s*\"?([^\"\n]+)\"?\s*$", text, re.M)
    return m.group(1).strip() if m else None


def check_metadata():
    problems = []
    cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    z = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
    if cff_value(cff, "license") != "AGPL-3.0-only" or z.get("license") != "AGPL-3.0-only":
        problems.append("licence must be AGPL-3.0-only in CITATION.cff and .zenodo.json")
    if cff_value(cff, "version") != z.get("version"):
        problems.append("version differs between CITATION.cff and .zenodo.json")
    if "0009-0000-9778-5374" not in cff or z["creators"][0].get("orcid") != "0009-0000-9778-5374":
        problems.append("creator ORCID missing or different")
    if "Brisson" not in cff or "Brisson" not in z["creators"][0]["name"]:
        problems.append("creator name missing")
    for key in ("title", "description", "upload_type"):
        if not z.get(key):
            problems.append(f".zenodo.json lacks {key}")
    ver = z.get("version")
    log = (ROOT / "CHANGELOG.md")
    if not log.exists() or ver not in log.read_text(encoding="utf-8"):
        problems.append(f"CHANGELOG.md does not mention version {ver}")
    return problems


def check_wording():
    problems = []
    for name in ("index.html", "README.md", "CHANGELOG.md", "CITATION.cff", ".zenodo.json"):
        p = ROOT / name
        if not p.exists():
            continue
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            low = line.lower()
            for phrase in BANNED:
                if phrase in low and not ALLOWED_NEGATION.search(low):
                    problems.append(f"{name}:{n}: unqualified wording '{phrase}'")
            if re.search("[\U0001F300-\U0001FAFF\u2600-\u27BF]", line):
                problems.append(f"{name}:{n}: emoji")
    return problems


def check_links_online(page):
    problems = []
    urls = sorted({h for h in page.hrefs if h.startswith("https://")})
    for u in urls:
        ok = False
        for _ in range(3):
            try:
                req = urllib.request.Request(u, method="HEAD", headers={"User-Agent": "link-check"})
                with urllib.request.urlopen(req, timeout=20) as r:
                    ok = r.status < 400
            except Exception:
                ok = False
            if ok:
                break
        if not ok:
            problems.append(f"link did not answer: {u}")
    return problems, len(urls)


def main(argv):
    all_problems = []
    html_problems, page = check_html(ROOT / "index.html")
    all_problems += html_problems
    js_problems, skipped = check_js(page)
    all_problems += [p for p in js_problems if not p.endswith("(skipped)")]
    all_problems += check_license() + check_metadata() + check_wording()
    n_links = len([h for h in page.hrefs if h.startswith("https://")])
    if "--online" in argv:
        lp, n_links = check_links_online(page)
        all_problems += lp
    for p in all_problems:
        print("FAIL", p)
    print(f"{len(page.ids)} ids, {n_links} external links, {len(page.scripts)} inline scripts, "
          f"{'online' if '--online' in argv else 'offline'} run, {len(all_problems)} problems")
    return 1 if all_problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
