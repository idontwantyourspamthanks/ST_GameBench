#!/usr/bin/env python3
"""Checks the wording table of patches/pm_tooltip.s: "name (key): effect" must fit the 52-character tooltip area (13 sixteen-pixel
columns x 4 characters), with the key label shown (qol_keys active) and without it; every table row has the right number of strings.
Entry format: dc.b COUNT,"name",0,"key",0,"effect",0 ... (key may be the empty string 0).   python3 tools/pmtt_check.py"""
import re
import sys
from pathlib import Path

s = (Path(__file__).resolve().parent.parent / "patches" / "pm_tooltip.s").read_text()
bad = 0
n = 0
longest = (0, "")
for m in re.finditer(r'^(e\d+):\s+dc\.b\s+(\d),(.*)$', s, re.M):
    cnt = int(m.group(2))
    # tokens: quoted strings and bare 0 terminators; an empty string is the lone 0 right after the name's 0
    toks = re.findall(r'"[^"]*"|\b0\b', m.group(3).replace('",3,"', "\x03"))
    strs, cur_open = [], False
    i = 0
    while i < len(toks):
        t = toks[i]
        if t.startswith('"'):
            strs.append(t[1:-1])
            if i + 1 < len(toks) and toks[i + 1] == "0":
                i += 1
        else:                       # a 0 that does not follow a string: an empty string
            strs.append("")
        i += 1
    if len(strs) != 2 + cnt:
        print(f"{m.group(1)}: count {cnt} but {len(strs) - 2} effect strings ({strs})")
        bad += 1
        continue
    name, key, effs = strs[0], strs[1], strs[2:]
    for e0 in effs:
        for k in ("", key):
            n += 1
            off, _, on = e0.partition("\x03")
            e = on if (k and on) else off
            line = name + (f" ({k})" if k else "") + ": " + e
            if len(line) > longest[0]:
                longest = (len(line), line)
            if len(line) > 52:
                print(f"TOO LONG {m.group(1)}: {len(line)} {line}")
                bad += 1
            if k == key == "":
                break
print(f"{n} texts checked (with and without keys), longest {longest[0]}: {longest[1]!r}, {bad} problems")
sys.exit(1 if bad else 0)
