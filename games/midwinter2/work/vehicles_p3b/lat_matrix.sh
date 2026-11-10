#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/midwinter2/work/vehicles_p3b
S1="raid_onfoot_dhafra.sav raid_jeep_dhafra.sav raid_helicopter_lobos.sav"
for mhz in 8 16; do for s in $S1; do
  for c in orig p3c; do echo "$c $s $mhz"; done
done; done > /tmp/lat_jobs.txt
for mhz in 8 16; do echo "p3b raid_helicopter_lobos.sav $mhz" >> /tmp/lat_jobs.txt; done
cat /tmp/lat_jobs.txt | xargs -P 2 -L 1 bash -c 'python3 latency.py $0 $1 $2 8 2>&1 | grep RESULT' > /tmp/lat_results.txt
