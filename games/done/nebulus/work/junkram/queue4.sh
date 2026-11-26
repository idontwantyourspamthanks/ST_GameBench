#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
J=work/junkram
O=$J/after.jsonl
for s in 201 202; do python3 $J/jr.py after megaste rs $s; done >> $O
for s in 211 212 213; do python3 $J/jr.py after megaste all $s; done >> $O
for s in 221 222 223 224; do python3 $J/jr.py after_relaxed megaste all $s; done >> $O
python3 $J/jr.py after megaste none 1 >> $O
echo done > $J/after.done
