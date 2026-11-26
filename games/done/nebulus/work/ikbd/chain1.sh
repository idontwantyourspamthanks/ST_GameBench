#!/bin/sh
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
while pgrep -f "r2.py fixed" > /dev/null; do sleep 2; done
for v in fwd fdr; do python3 work/ikbd/mksnap.py $v 2380; done
python3 work/ikbd/r2.py fwd work/ikbd/iso_fwd.jsonl 0.4 1.0
python3 work/ikbd/r2.py fdr work/ikbd/iso_fdr.jsonl 0.4 1.0
for v in patched orig fixed; do python3 work/ikbd/r5.py $v 24 7 work/ikbd/rand_$v.jsonl; done
echo CHAIN1 DONE
