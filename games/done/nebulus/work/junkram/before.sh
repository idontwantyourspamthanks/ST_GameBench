#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
O=work/junkram/before.jsonl
for s in 11 12 13; do python3 work/junkram/jr.py before ste rs $s; done >> $O
for s in 21 22 23; do python3 work/junkram/jr.py before ste all $s; done >> $O
python3 work/junkram/jr.py before ste none 1 >> $O
for s in 31 32; do python3 work/junkram/jr.py before megaste rs $s; done >> $O
python3 work/junkram/jr.py before megaste all 41 >> $O
echo done > work/junkram/before.done
