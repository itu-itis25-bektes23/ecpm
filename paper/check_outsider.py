#!/usr/bin/env python3
"""Check that every outsider-test answer key occurs in its reader's tex region.

Usage: python3 check_outsider.py TEX_PATH [QUESTIONS_MD]
Exit 0: all keys found. Exit 1: at least one miss. Exit 2: could not run.
A stated line that does not contain its key is reported as a warning only.
"""
import os
import re
import sys

DEFAULT_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "..", "..", "deliverables", "outsider_test.md")


def cannot(msg):
    print("could not run: " + msg)
    sys.exit(2)


def find(text, s, start=0):
    i = text.find(s, start)
    if i < 0:
        cannot("marker %r not found in tex" % s)
    return i


def regions(tex):
    a0 = find(tex, "\\begin{abstract}")
    i_end = find(tex, "% ===== end sections/01_introduction.tex =====", a0)
    c0 = find(tex, "\\caption{", i_end)  # first caption after intro = Figure 1
    c1 = find(tex, "\n", c0)
    app = find(tex, "\n\\appendix", a0)
    short = tex[a0:i_end] + "\n" + tex[c0:c1]
    return {"2": short, "15": tex[a0:app]}


def parse(md):
    qs, section = [], None
    cur = None
    for line in md.splitlines():
        if line.startswith("## "):
            section = "2" if line.startswith("## 2-minute") else "15" if line.startswith("## 15-minute") else None
        m = re.match(r"^(Q\d+)\.", line)
        if m:
            cur = {"id": m.group(1), "reader": section}
            qs.append(cur)
        m = re.match(r"^Answer key: `(.+)`\s*$", line)
        if m and cur is not None:
            cur["key"] = m.group(1)
        m = re.match(r"^Tex line: (\d+)", line)
        if m and cur is not None:
            cur["line"] = int(m.group(1))
    return qs


def main(argv):
    if len(argv) < 2:
        cannot("usage: check_outsider.py TEX_PATH [QUESTIONS_MD]")
    md_path = argv[2] if len(argv) > 2 else DEFAULT_MD
    try:
        tex = open(argv[1], encoding="utf-8").read()
        md = open(md_path, encoding="utf-8").read()
    except OSError as e:
        cannot(str(e))
    if not tex.strip():
        cannot("tex file is empty: " + argv[1])
    regs = regions(tex)
    qs = parse(md)
    if not qs:
        cannot("no questions parsed from " + md_path)
    lines = tex.splitlines()
    misses = 0
    for q in qs:
        if q.get("reader") not in regs or "key" not in q:
            cannot("%s has no reader section or answer key" % q["id"])
        ok = q["key"] in regs[q["reader"]]
        if not ok:
            misses += 1
        note = ""
        ln = q.get("line")
        if ok and ln and not (1 <= ln <= len(lines) and q["key"] in lines[ln - 1]):
            note = "  (warning: not on stated line %d)" % ln
        print("%s %-4s %s-min  %r%s" % ("OK  " if ok else "MISS", q["id"], q["reader"], q["key"], note))
    n2 = sum(q["reader"] == "2" for q in qs)
    print("%d questions (%d two-minute, %d fifteen-minute), %d missing" % (len(qs), n2, len(qs) - n2, misses))
    sys.exit(1 if misses else 0)


if __name__ == "__main__":
    main(sys.argv)
