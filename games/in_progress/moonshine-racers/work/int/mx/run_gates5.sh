#!/usr/bin/env bash
cd "$(dirname "$0")"
for spec in "12 330" "5 520"; do set -- $spec; L=$1; N=$2
  for v in "A 8" "X 16" "X 32"; do set -- $v; python3 pixcap.py $1 ste1m_race_drive.sav $2 $N pix/L${L}_$1$2 40 102c=$(printf %04x $L) 6105=01 hold 2>&1 | tail -1; done
done
echo DONE
