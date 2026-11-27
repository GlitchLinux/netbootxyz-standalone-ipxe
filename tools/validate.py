#!/usr/bin/env python3
"""Validate standalone scripts: shebang, no stray exit, all literal gotos resolve, no dup labels."""
import os, re, sys
from collections import Counter

D = sys.argv[1]
bad = 0
for f in sorted(os.listdir(D)):
    if not f.endswith(".ipxe"):
        continue
    t = open(os.path.join(D, f)).read()
    errs = []
    if not t.startswith("#!ipxe\n"):
        errs.append("no shebang")
    body = t.split(":nbx_quit", 1)[0]
    for i, l in enumerate(body.split("\n"), 1):
        if l.lstrip().startswith("#") or l.lstrip().startswith("echo"):
            continue
        if re.search(r"(^\s*|&&\s*|\|\|\s*)exit\b", l):
            errs.append(f"stray exit L{i}: {l.strip()}")
    labels = re.findall(r"^\s*:([A-Za-z0-9_.-]+)\s*$", t, re.M)
    dups = [k for k, c in Counter(labels).items() if c > 1]
    if dups:
        errs.append(f"duplicate labels {dups}")
    missing = set(re.findall(r"\bgoto\s+([A-Za-z0-9_.-]+)(?=\s|$)", t)) - set(labels)
    if missing:
        errs.append(f"unresolved gotos {sorted(missing)}")
    if "set menu " + f[:-5] not in t:
        errs.append("menu not set")
    if errs:
        bad += 1
        print(f, "\n  " + "\n  ".join(errs))
print(f"checked {len([x for x in os.listdir(D) if x.endswith('.ipxe')])} files, {bad} with problems")
