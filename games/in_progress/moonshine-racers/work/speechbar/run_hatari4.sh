#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
R=work/speechbar/res; S=work/speechbar
while ! grep -q STAGEDONE $R/h3_log.txt 2>/dev/null; do sleep 10; done
L=$R/cold_log.txt
for cfg in "ste 1024 1.62 ste1m" "ste 4096 1.62 ste4m" "megaste 1024 2.06 mste1m"; do
  set -- $cfg
  echo "=== sb HD cold $1 $2 $3" >> $L
  timeout 2400 python3 $S/cold_sb.py $1 $2 $3 build/sb_hd $4 0,16 >> $L 2>&1
done
echo COLDDONE >> $L
