#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/midwinter2/work/vehicles_p3b
for mhz in 8 16; do for s in raid_onfoot_dhafra.sav raid_jeep_dhafra.sav raid_helicopter_lobos.sav; do
  for c in p3c p3cp; do echo "$c $s $mhz"; done
done; done > /tmp/lat_jobs2.txt
cat /tmp/lat_jobs2.txt | xargs -P 2 -L 1 bash -c 'python3 latency.py $0 $1 $2 8 2>&1 | grep -E "RESULT|Error"' > /tmp/lat_results2.txt
cat /tmp/lat_results2.txt
