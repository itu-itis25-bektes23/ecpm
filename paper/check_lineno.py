"""Count line numbers placed in the column gutter instead of the outer margins (ACL review layout).
A line number is a word of 3 to 4 digits in the ruler font left of x=60pt or right of W-60pt (correct),
or within 12pt of the page centre (misplaced). Ruler digits are under 8.5pt tall, body text is taller. Exit 1 on any misplaced, 2 if no line numbers found."""
import re, subprocess, sys
html = subprocess.run(["pdftotext", "-bbox", sys.argv[1], "-"], capture_output=True, text=True).stdout
ok = bad = 0; where = {}
for i, pg in enumerate(html.split("<page ")[1:], 1):
    W = float(re.search(r'width="([\d.]+)"', pg).group(1))
    for x0, y0, x1, y1, w in re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(\d{3,4})</word>', pg):
        x0, x1 = float(x0), float(x1); c = (x0 + x1) / 2
        if float(y1) - float(y0) > 8.5: continue  # body text, not the ruler font
        if x1 < 60 or x0 > W - 60: ok += 1
        elif abs(c - W / 2) < 12: bad += 1; where[i] = where.get(i, 0) + 1
if ok + bad == 0: print("COULD NOT RUN: no line numbers found"); sys.exit(2)
print(f"line numbers: {ok} in margins, {bad} in the gutter" + (f" (pages {where})" if bad else ""))
sys.exit(1 if bad else 0)
