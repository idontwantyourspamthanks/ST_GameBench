#!/usr/bin/env python3
"""Summarise work/campgate/logs/*.txt (one raw log per gate run) into a markdown table: python3 summarize.py > RESULTS.md"""
import re, sys
from pathlib import Path
L = Path(__file__).resolve().parent / "logs"
rows = []
for f in sorted(L.glob("*.txt")):
    t = f.read_text(errors="replace")
    m = re.search(r"^== (\S+) done: (.*)$", t, re.M)
    n_pass = len(re.findall(r"^CHECK .*: PASS", t, re.M)); n_fail = len(re.findall(r"^CHECK .*: FAIL", t, re.M))
    loads = re.findall(r"^(?:LOAD \w+|CASE good\w*): .*?loaded=True ([\d.]+)s", t, re.M)
    err = re.search(r"bus/address error lines (\d+)", t)
    ps = re.search(r"^PSGCHECK ok (\S+) violations (\S+) warnings (\S+)", t, re.M)
    status = (m.group(2).split(";")[0] if m else "no result line (run did not finish)")
    rows.append((f.stem, status, n_pass, n_fail, ",".join(loads[:3]), err.group(1) if err else "", f"ok={ps.group(1)} viol={ps.group(2)} warn={ps.group(3)}" if ps else ""))
print("| run (log work/campgate/logs/NAME.txt) | result | checks PASS/FAIL | load (emu s) | Bus/Addr lines | PSGCHECK |")
print("|---|---|---|---|---|---|")
for r in rows:
    print(f"| {r[0]} | {r[1]} | {r[2]}/{r[3]} | {r[4]} | {r[5]} | {r[6]} |")
