#!/usr/bin/env python3
"""Check that every verbatim prompt block in a tex file matches the harness.

Stdlib only. Each block must be preceded by "% prompt-source: <key>" (as
written by paper/gen_prompt_appendix.py). The checker re-runs (or reuses) the
dry-run artifacts, takes the exact text the harness sent for <key>, applies
the same shortening and 48-column wrapping, and requires the block to be
byte-identical. It also requires that, ignoring line breaks, the block's
words equal the sent text's words (so the wrapping cannot hide an edit).

Exit status: 0 all blocks match, 1 at least one mismatch,
2 could not run (missing/empty file, no tagged blocks, dry runs failed).

Usage: python3.12 -B paper/check_prompts.py [TEX] [--dry-dir DIR]
"""
import argparse
import difflib
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_prompt_appendix as gen  # noqa: E402

BLOCK = re.compile(r"% prompt-source: (\S+)\n\{\\scriptsize\n\\begin\{verbatim\}\n"
                   r"(.*?)\n\\end\{verbatim\}", re.S)
# Blocks whose text is not stored in the artifacts; checked against the code
# path the harness calls instead.
CODE_SOURCED = {"agent_system", "agent_system_model_first_suffix"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tex", nargs="?", default=gen.DEFAULT_OUT)
    ap.add_argument("--dry-dir", default=None)
    args = ap.parse_args()
    try:
        with open(args.tex, encoding="utf-8") as fh:
            tex = fh.read()
    except OSError as exc:
        print(f"COULD NOT RUN: {exc}")
        return 2
    blocks = BLOCK.findall(tex)
    if not blocks:
        print(f"COULD NOT RUN: no '% prompt-source:' verbatim blocks in {args.tex}")
        return 2
    dry_dir = args.dry_dir or tempfile.mkdtemp(prefix="ecpm_promptcheck_")
    try:
        os.makedirs(dry_dir, exist_ok=True)
        gen.make_dry_runs(dry_dir)
        src = gen.sources(dry_dir)
    except Exception as exc:  # noqa: BLE001
        print(f"COULD NOT RUN: dry runs failed: {exc!r}")
        return 2
    failures = 0
    for key, body in blocks:
        if key not in src:
            print(f"FAIL {key}: unknown prompt source")
            failures += 1
            continue
        expected = gen.render_block(src[key])
        words_ok = (body.split() == expected.split())
        if body == expected and words_ok:
            where = ("code path (not stored in artifact)" if key in CODE_SOURCED
                     else "dry-run artifact")
            print(f"PASS {key}: byte-identical to {where}")
            continue
        failures += 1
        print(f"FAIL {key}: block differs from what the harness sends")
        for line in difflib.unified_diff(expected.split("\n"), body.split("\n"),
                                         "harness", "tex", lineterm="", n=1):
            print("    " + line)
    print(f"{len(blocks) - failures}/{len(blocks)} blocks match (dry runs in {dry_dir})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
