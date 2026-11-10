#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/midwinter2/work/vehicles_p3b
: > /tmp/lat_jobs3.txt
for mhz in 8 16; do for s in raid_onfoot_dhafra.sav raid_jeep_dhafra.sav raid_helicopter_lobos.sav; do
  for c in p3c p3cp; do echo "$c $s $mhz" >> /tmp/lat_jobs3.txt; done
done; echo "p3b raid_helicopter_lobos.sav $mhz" >> /tmp/lat_jobs3.txt; done
cat /tmp/lat_jobs3.txt | xargs -P 2 -L 1 bash -c 'python3 latency.py $0 $1 $2 10 2>&1 | grep -E "RESULT|EXTRA|Error"' > /tmp/lat_results3.txt
cat /tmp/lat_results3.txt
