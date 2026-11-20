#!/bin/bash
# cold boot the campaign build b5 to the title: ST/Mega ST/STE/Mega STE at 2 and 4 MB (title memstates for the gates)
cd "$(dirname "$0")"
for cfg in "ste 2048 ste2m" "ste 4096 ste4m" "megaste 2048 mste2m" "megaste 4096 mste4m" "st 2048 st2m" "st 4096 st4m" "megast 2048 mst2m" "megast 4096 mst4m"; do
  set -- $cfg
  ./env.sh python3 probe_type.py --game ../camphd/b5 --machine $1 --mem $2 --out snap/b5_$3 > boot_b5_$3.txt 2>&1
done
