#!/usr/bin/env python3
"""Offline pointer detector for saved TT shots: reads 'tag ... px=.. py=..' lines from a log and counts the pointer's WHITE ring pixels (r,g,b > 215)
and orange arrow pixels in a window around the pointer. usage: detect.py DIR LOG"""
import sys, re
from pathlib import Path
from PIL import Image
d, log = Path(sys.argv[1]), sys.argv[2]
for line in open(log):
    m = re.search(r'(\S+) mode=(\d+).*px=(\d+) py=(\d+)', line)
    if not m: continue
    tag, mode, px, py = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
    f = d / f'{tag}.png'
    if not f.exists(): continue
    im = Image.open(f).convert('RGB'); p = im.load(); w = o = 0
    for yy in range(max(0,2*py-16), 2*py+30):
        for xx in range(max(0,2*px-16), 2*px+26):
            if xx < im.width and yy < 400:
                r,g,b = p[xx,yy]
                if r>215 and g>215 and b>215: w += 1
                elif r>200 and 50<g<140 and b<80: o += 1
    print(f'{tag} mode={mode} px={px} py={py} white={w} orange={o} -> {"PTR" if (140<=o<=190 or 12<=w<=100) else "none"}')
