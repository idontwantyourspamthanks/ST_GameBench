#!/usr/bin/env bash
# Is the Mega STE 8 MHz "TOS stuck in boot-sector retry" flake pre-existing?  Same Hatari flags, shipped v1.6 vs candidate, 3 cold boots each (bootgate: boot -> orange prompt).
cd "$(dirname "$0")"
export MW2S_SOUND=50066 MW2S_EXTRA="--trace fdc,psg_write"
for i in 1 2 3; do
  for v in ship:/tmp/mw2s/ship c17:/tmp/mw2s/c17; do
    n=fl_${v%%:*}_mste8_$i
    timeout 800 python3 bootgate.py $n megaste 8 ${v#*:} --expect any > out/$n.log 2>&1
    echo "$n: $(grep -E '^prompt' out/$n.log) | $(grep -E '^GATE' out/$n.log | cut -c1-120)"
  done
done
