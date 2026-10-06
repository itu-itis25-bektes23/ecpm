"""Independent anonymity check: reads raw bytes of every file (not the scrubber's view).
Exit 0 = pass, 1 = identifying content found, 2 = nothing examined (could not run)."""
import os, re, sys, subprocess
PAT = re.compile(rb'(bektes|henne|koulatzidis|zwierzynski|algorithmmaster|itu-itis25|itu\.edu|tum\.de|pjwstk|orcid\.org/\d|/Users/[a-z]|/home/[a-z]{3,})', re.I)
EMAIL = re.compile(rb'[\w.+-]+@[\w-]+\.[a-z]{2,}', re.I)
root = sys.argv[1]; n = 0; hits = []
for d, _, fs in os.walk(root):
    for f in fs:
        p = os.path.join(d, f); n += 1
        b = open(p, 'rb').read()
        for m in PAT.finditer(b): hits.append((p, m.group(0)[:40]))
        for m in EMAIL.finditer(b):
            if m.group(0).lower() not in (b'anonymous@example.org',) and not m.group(0).endswith((b'.png', b'.py', b'.svg')):
                hits.append((p, m.group(0)[:40]))
        if f.endswith('.pdf'):
            info = subprocess.run(['pdfinfo', p], capture_output=True, text=True).stdout
            for line in info.splitlines():
                if line.startswith(('Author:', 'Title:', 'Subject:', 'Keywords:')) and line.split(':', 1)[1].strip():
                    hits.append((p, line[:60].encode()))
if n == 0: print('COULD NOT RUN: no files examined'); sys.exit(2)
print(f'examined {n} files, {len(hits)} identifying hits')
for h in hits[:12]: print('  ', h[0].replace(root, ''), h[1])
sys.exit(1 if hits else 0)
