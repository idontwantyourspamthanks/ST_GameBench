#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2/work/scratch/disks
run(){ timeout 1200 python3 mtt.py "$@" >> chainC.log 2>&1; }
: > chainC.log
run ICS91.st ics91_tt 4096 ics tt 3.06
run ICS91.st ics91_falcon 4096 ics falcon 4.04
run ICS91.st ics91_mste 2048 ics megaste 2.06
echo CHAIN-DONE >> chainC.log
