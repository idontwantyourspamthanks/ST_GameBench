#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/midwinter2/work/vehicles_p3b
: > /tmp/vg/batch3_32.txt
for t in "3 allin" "4 stand" "6 stand" "6 movturn" "19 allin" "14 allin"; do python3 runtype.py $t P --mhz 32 >> /tmp/vg/batch3_32.txt 2>&1; done
echo DONE >> /tmp/vg/batch3_32.txt
