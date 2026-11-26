#!/bin/bash
# waits for the STE part of before.sh (7 boots), stops it, then runs the after-fix evidence in one-Hatari-at-a-time order
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
J=work/junkram
while [ $(wc -l < $J/before.jsonl) -lt 7 ]; do sleep 5; done
kill 1252998; sleep 1
for p in $(pgrep -f "work/junkram/jr.py before megaste"); do kill $p; done
sleep 3
O=$J/after.jsonl
python3 $J/relaunch.py after ste warm >> $J/relaunch.jsonl
python3 $J/relaunch.py after ste f9 >> $J/relaunch.jsonl
python3 $J/relaunch.py before ste warm >> $J/relaunch.jsonl
for s in 101 102 103 104; do python3 $J/jr.py after ste rs $s; done >> $O
for s in 111 112 113 114; do python3 $J/jr.py after ste all $s; done >> $O
for s in 121 122 123 124; do python3 $J/jr.py after_relaxed ste all $s; done >> $O
echo done > $J/after_ste.done
for s in 201 202 203; do python3 $J/jr.py after megaste rs $s; done >> $O
for s in 211 212 213; do python3 $J/jr.py after megaste all $s; done >> $O
for s in 221 222 223; do python3 $J/jr.py after_relaxed megaste all $s; done >> $O
python3 $J/relaunch.py after megaste warm >> $J/relaunch.jsonl
echo done > $J/after.done
