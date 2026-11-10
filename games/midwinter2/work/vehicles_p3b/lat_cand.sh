#!/bin/bash
# input latency + overshoot (latency.py): orig vs the candidate, foot (5), Jeep, Helicopter, 8 / 16 MHz, 10 trials each
cd /home/ryan/Code/AtariST/gamebench/games/midwinter2/work/vehicles_p3b
: > /tmp/latc_jobs.txt
for mhz in 8 16; do for s in raid_onfoot_dhafra.sav raid_jeep_dhafra.sav raid_helicopter_lobos.sav; do for c in orig cand; do echo "$c $s $mhz" >> /tmp/latc_jobs.txt; done; done; done
cat /tmp/latc_jobs.txt | xargs -P ${NP:-2} -L 1 bash -c 'python3 latency.py $0 $1 $2 10 2>&1 | grep -E "RESULT|EXTRA|Error|Trace"' > /tmp/latc_results.txt
echo DONE >> /tmp/latc_results.txt
cat /tmp/latc_results.txt
