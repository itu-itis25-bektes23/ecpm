"""Report where the main text ends: page and column position of the 'Limitations' heading.
Main length = (page - 1) + fraction, with two columns each counted as half a page.
Exit 1 if over the budget (default 7.5), 2 if the heading is not found. Usage: page_budget.py PDF [budget]"""
import re, subprocess, sys
pdf = sys.argv[1]; budget = float(sys.argv[2]) if len(sys.argv) > 2 else 7.5
html = subprocess.run(["pdftotext", "-bbox", pdf, "-"], capture_output=True, text=True).stdout
pages = html.split("<page ")[1:]
for i, pg in enumerate(pages, 1):
    W, H = (float(x) for x in re.search(r'width="([\d.]+)" height="([\d.]+)"', pg).groups())
    for m in re.finditer(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="[\d.]+" yMax="[\d.]+">Limitations</word>', pg):
        x, y = float(m.group(1)), float(m.group(2))
        top, bot = 0.075 * H, 0.91 * H  # A4 ACL text block
        col_frac = min(1, max(0, (y - top) / (bot - top)))
        frac = (0.5 if x > W / 2 else 0.0) + 0.5 * col_frac
        length = i - 1 + frac
        print(f"Limitations on page {i}, {'right' if x > W/2 else 'left'} column at {col_frac:.0%}: main text = {length:.2f} pages (budget {budget})")
        sys.exit(0 if length <= budget else 1)
print("COULD NOT RUN: heading not found"); sys.exit(2)
