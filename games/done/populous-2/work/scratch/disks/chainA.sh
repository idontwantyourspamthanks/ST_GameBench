#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2/work/scratch/disks
run(){ timeout 900 python3 matrix.py "$@" >> chainA.log 2>&1; }
: > chainA.log
while pgrep -f "matrix.py ICS91.st ics91_2m" >/dev/null; do sleep 5; done
run Vmax.st vmax_1m 1024 ics
run Vmax.st vmax_2m 2048 ics
run "ICS[a].st" icsa_1m 1024 ics
run Illegal.st ill_512 512 ics
run Illegal.st ill_1m 1024 ics
echo CHAIN-DONE >> chainA.log
