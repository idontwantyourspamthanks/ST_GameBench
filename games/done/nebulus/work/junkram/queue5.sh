#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
J=work/junkram
while [ ! -f $J/after.done ]; do sleep 3; done
O=$J/leftover.jsonl
python3 $J/capture.py after ste after_ste > $J/capture_ste.log 2>&1
python3 $J/jr.py after ste leftover:after_ste 301 >> $O
python3 $J/jr.py before ste leftover:after_ste 302 >> $O
echo done > $J/queue5.done
