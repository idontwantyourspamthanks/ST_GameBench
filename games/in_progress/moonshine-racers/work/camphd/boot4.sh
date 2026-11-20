#!/bin/bash
# cold boot the campaign build b3 to the title on the four 2 MB+ machines (title memstate + RAM header peeks)
cd "$(dirname "$0")"
for cfg in "ste 2048 ste2m" "ste 4096 ste4m" "megaste 2048 mste2m" "megaste 4096 mste4m"; do
  set -- $cfg
  ./env.sh python3 title_snap.py --game ../camphd/b3 --machine $1 --mem $2 --out snap/b3_$3 > boot_b3_$3.txt 2>&1
done
