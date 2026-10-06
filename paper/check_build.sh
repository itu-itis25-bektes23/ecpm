#!/usr/bin/env bash
# Build gate for ECPM_main.tex. Usage: ./check_build.sh [draft|nores|final]
# draft: placeholders allowed (shown grey). final: any \PH / \pending stops the build.
# Both modes fail on: LaTeX errors, undefined references or citations, "??" in the PDF,
# Type 3 fonts, unembedded fonts. Outputs are deleted first so their existence proves this run.
set -u
MODE=${1:-draft}; DOC=ECPM_main
rm -f $DOC.pdf $DOC.aux $DOC.bbl $DOC.log
SRC=$DOC.tex
if [ "$MODE" = final ]; then sed 's/\\newif\\ifdraft \\drafttrue/\\newif\\ifdraft \\draftfalse/' $DOC.tex > ${DOC}_final.tex; SRC=${DOC}_final.tex; DOC=${DOC}_final; fi
# nores: everything final except model-result slots (\RES), which stay grey. Any \PH or \pending fails.
if [ "$MODE" = nores ]; then sed -e 's/\\newif\\ifdraft \\drafttrue/\\newif\\ifdraft \\draftfalse/' -e 's/\\newif\\ifresallowed \\resallowedfalse/\\newif\\ifresallowed \\resallowedtrue/' $DOC.tex > ${DOC}_nores.tex; SRC=${DOC}_nores.tex; DOC=${DOC}_nores
  grep -q 'resallowedtrue' $SRC || { echo "FAIL: nores switch not found in source"; exit 1; }; fi
run() { pdflatex -interaction=nonstopmode -halt-on-error $SRC > /dev/null 2>&1; }
run || { echo "FAIL: LaTeX error (see $DOC.log)"; grep -m3 '^!' $DOC.log; exit 1; }
bibtex $DOC > /dev/null 2>&1 || { echo "FAIL: bibtex"; exit 1; }
run && run || { echo "FAIL: LaTeX error on rerun"; grep -m3 '^!' $DOC.log; exit 1; }
[ -f $DOC.pdf ] || { echo "FAIL: no PDF produced"; exit 1; }
if grep -q 'undefined' $DOC.log; then echo "FAIL: undefined references or citations"; grep -m5 'undefined' $DOC.log; exit 1; fi
if [ "$MODE" != draft ]; then ob=$(grep -E '^Overfull \\[hv]box \(([0-9]+\.[0-9]+)pt' $DOC.log | awk -F'[(p]' '$2+0>1.0' | wc -l); [ "$ob" -eq 0 ] || { echo "FAIL: $ob overfull boxes above 1pt"; grep -m5 '^Overfull' $DOC.log; exit 1; }; fi
n=$(pdftotext $DOC.pdf - 2>/dev/null | grep -c '??'); [ "$n" -eq 0 ] || { echo "FAIL: $n lines with ?? in the PDF"; exit 1; }
pdffonts $DOC.pdf 2>/dev/null | grep -q 'Type 3' && { echo "FAIL: Type 3 font"; exit 1; }
pdffonts $DOC.pdf 2>/dev/null | awk 'NR>2 && $(NF-4)!="yes"{bad=1} END{exit bad}' || { echo "FAIL: unembedded font"; exit 1; }
echo "PASS ($MODE): $(pdfinfo $DOC.pdf | awk '/Pages/{print $2}') pages"
