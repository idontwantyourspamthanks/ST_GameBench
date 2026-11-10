#!/bin/bash
# batch.sh OUT SET SCENARIOS... ; types from $TYPES
out=$1; set=$2; shift 2
cd /home/ryan/Code/AtariST/gamebench/games/midwinter2/work/vehicles_p3b
: > $out
for t in ${TYPES:-5 1 2 3 0 4 7 6 10 19 21 9 8 11 12 13 14 15 16 17 18 20}; do
  for s in "$@"; do
    python3 runtype.py $t $s $set >> $out 2>&1
  done
done
echo DONE >> $out
