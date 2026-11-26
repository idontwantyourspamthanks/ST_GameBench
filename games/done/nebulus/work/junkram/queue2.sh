#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
J=work/junkram
while [ ! -f $J/after.done ]; do sleep 5; done
O=$J/leftover.jsonl
python3 $J/capture.py after ste after_ste > $J/capture_ste.log 2>&1
python3 $J/jr.py after ste leftover:after_ste 301 >> $O
python3 $J/jr.py before ste leftover:after_ste 302 >> $O
python3 $J/jr.py after_relaxed ste leftover:after_ste 303 >> $O
python3 $J/dumpcmp.py before ste >> $J/dumpcmp.jsonl
python3 $J/dumpcmp.py after ste >> $J/dumpcmp.jsonl
python3 $J/capture.py after megaste after_megaste > $J/capture_mega.log 2>&1
python3 $J/jr.py after megaste leftover:after_megaste 311 >> $O
python3 $J/jr.py after megaste leftover:after_megaste 312 >> $O
echo done > $J/queue2.done
