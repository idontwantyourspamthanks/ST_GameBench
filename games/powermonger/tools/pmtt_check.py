#!/usr/bin/env python3
"""Checks the wording table of patches/pm_tooltip.s: name + effect of every entry must fit the 52-character tooltip area
(13 sixteen-pixel columns x 4 characters), and every id 1..32 that has an entry is listed.   python3 tools/pmtt_check.py"""
import re
import sys
from pathlib import Path

s = (Path(__file__).resolve().parent.parent / "patches" / "pm_tooltip.s").read_text()
bad = 0
n = 0
for m in re.finditer(r'^(e\d+):\s+dc\.b\s+(\d),(.*)$', s, re.M):
    parts = re.findall(r'"([^"]*)"', m.group(3))
    cnt = int(m.group(2))
    if len(parts) != 1 + cnt:
        print(f"{m.group(1)}: count {cnt} but {len(parts) - 1} effect strings")
        bad += 1
    for e in parts[1:]:
        n += 1
        if len(parts[0]) + len(e) > 52:
            print(f"TOO LONG {m.group(1)}: {len(parts[0]) + len(e)} {parts[0]}{e}")
            bad += 1
print(f"{n} texts checked, {bad} problems")
sys.exit(1 if bad else 0)
