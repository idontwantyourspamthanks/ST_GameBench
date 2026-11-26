#!/bin/bash
# usage: dis.sh START END  (hex, no $)  -> disassembly lines of work/hud/dis/all_7000_19000.txt in range
python3 - "$1" "$2" <<'P'
import sys,re
a,b=int(sys.argv[1],16),int(sys.argv[2],16)
for ln in open('work/hud/dis/all_7000_19000.txt'):
    m=re.match(r'([0-9a-f]{6}):',ln)
    if m and a<=int(m.group(1),16)<=b: print(ln,end='')
P
