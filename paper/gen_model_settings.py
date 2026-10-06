#!/usr/bin/env python3
"""Fill the Table 8 (tab:models) setting macros from run artifacts.

Stdlib only. Walks RUNS_DIR for *.json artifacts whose top level has a
"model" object ({"provider": ..., "model": ...}), assigns each to one of the
five table rows by its model id, and prints a \\newcommand block. A macro
gets a value only when an artifact field supplies it; otherwise it stays
\\RES{} (assumed defined elsewhere: grey "set at run" text). Nothing is
inferred from experiments/models.json or from defaults.

Fields read (all optional), from artifact["model"] unless noted:
  model, provider, base_url (or endpoint), served_model / response_model
  (the id the provider reported), quantization, runtime, thinking,
  reasoning_provenance.mode (on/off; "unspecified" counts as missing),
  timestamps: artifact created_utc / completed_utc / persistence_events[*].created_utc.

Usage: python3.12 -B paper/gen_model_settings.py RUNS_DIR [--out FILE]
"""
import argparse
import glob
import json
import os
import re
import sys
import urllib.parse

ROWS = {  # row key -> regex on the requested model id (case-insensitive)
    "Gemma": r"gemma-4-e4b",
    "GPTfour": r"^gpt-4o",
    "Sol": r"^gpt-5\.6-sol",
    "DeepSeek": r"deepseek-v4-flash",
    "Kimi": r"^kimi-k2\.7-code",
}
# Every macro the table uses, in output order.
MACROS = ["mGemmaQuant", "mGemmaRuntime", "mAccessGemma",
          "mGPTfourSnapshot", "mAccessGPTfour",
          "mAccessSol",
          "mDeepSeekThinking", "mDeepSeekProvider", "mAccessDeepSeek",
          "mAccessKimi"]
DATED = re.compile(r"\d{4}-\d{2}-\d{2}$")


def tex_escape(s):
    return (str(s).replace("\\", r"\textbackslash{}").replace("_", r"\_")
            .replace("%", r"\%").replace("&", r"\&").replace("#", r"\#")
            .replace("$", r"\$").replace("{", r"\{").replace("}", r"\}"))


def tt(s):
    return r"\texttt{" + tex_escape(s) + "}"


def artifacts(runs_dir):
    for path in sorted(glob.glob(os.path.join(runs_dir, "**", "*.json"),
                                 recursive=True)):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        m = data.get("model") if isinstance(data, dict) else None
        if isinstance(m, dict) and m.get("model") and m.get("provider") != "dry-run":
            yield path, data, m


def row_of(model_id):
    for key, pat in ROWS.items():
        if re.search(pat, model_id, re.I):
            return key
    return None


def timestamps(data):
    out = [data.get("created_utc"), data.get("completed_utc")]
    for ev in data.get("persistence_events") or []:
        if isinstance(ev, dict):
            out.append(ev.get("created_utc"))
    return [t[:10] for t in out if isinstance(t, str) and DATED.match(t[:10])]


def date_range(dates):
    if not dates:
        return None
    lo, hi = min(dates), max(dates)
    return lo if lo == hi else f"{lo} to {hi}"


def one_value(values):
    """A field is filled only if every artifact for the row agrees."""
    vals = sorted({v for v in values if v not in (None, "")}, key=str)
    if not vals:
        return None
    if len(vals) > 1:
        return "MIXED: " + ", ".join(map(str, vals))
    return vals[0]


def collect(runs_dir):
    rows = {k: [] for k in ROWS}
    for path, data, m in artifacts(runs_dir):
        key = row_of(str(m["model"]))
        if key:
            rows[key].append((path, data, m))
    return rows


def fill(rows):
    val = {name: None for name in MACROS}

    def field(key, *names):
        return one_value(m.get(n) for _, _, m in rows[key] for n in names)

    def access(key):
        return date_range([d for _, data, _ in rows[key] for d in timestamps(data)])

    def thinking(key):
        explicit = field(key, "thinking")
        if explicit is not None:
            return explicit
        modes = [(m.get("reasoning_provenance") or {}).get("mode")
                 for _, _, m in rows[key]]
        return one_value(x for x in modes if x in ("on", "off"))

    def provider(key):
        prov = field(key, "provider")
        url = field(key, "base_url", "endpoint")
        if prov is None:
            return None
        host = urllib.parse.urlsplit(url).hostname if url and "://" in str(url) else None
        return tt(prov) + (f" ({tt(host)})" if host else "")

    q = field("Gemma", "quantization")
    val["mGemmaQuant"] = tex_escape(q) if q else None
    r = field("Gemma", "runtime")
    val["mGemmaRuntime"] = tex_escape(r) if r else None
    snap = field("GPTfour", "served_model", "response_model")
    if snap is None:
        requested = field("GPTfour", "model")
        snap = requested if requested and re.search(r"\d{4}-\d{2}-\d{2}", requested) else None
    val["mGPTfourSnapshot"] = tt(snap) if snap else None
    t = thinking("DeepSeek")
    val["mDeepSeekThinking"] = tex_escape(t) if t else None
    val["mDeepSeekProvider"] = provider("DeepSeek")
    for key in ROWS:
        val["mAccess" + key] = access(key)
    return val


def render(val, rows):
    lines = ["% Table 8 model settings. Generated by paper/gen_model_settings.py;",
             "% \\RES{} = not recorded in any artifact under the runs dir."]
    for key in ROWS:
        lines.append(f"%   {key}: {len(rows[key])} artifact(s)")
    for name in MACROS:
        lines.append(f"\\newcommand{{\\{name}}}{{{val[name] or chr(92) + 'RES{}'}}}")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs_dir")
    ap.add_argument("--out", default="-")
    args = ap.parse_args()
    if not os.path.isdir(args.runs_dir):
        print(f"not a directory: {args.runs_dir}", file=sys.stderr)
        return 2
    rows = collect(args.runs_dir)
    text = render(fill(rows), rows)
    if args.out == "-":
        sys.stdout.write(text)
    else:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
