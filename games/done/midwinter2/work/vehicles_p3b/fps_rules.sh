#!/bin/bash
# fps_rules.sh: strict (-6) / middle (0) / none (1000) rule x on foot, Jeep, Speedboat, Crawler, Helicopter x stand, move x 8/16/32 MHz.  Output /tmp/fpsr_results.txt
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/vehicles_p3b
: > /tmp/fpsr_jobs.txt
for slk in 0 -6 1000; do for sc in stand move; do for m in 16 32 8; do for s in raid_onfoot_dhafra raid_jeep_dhafra raid_speedboat_iquitos raid_crawler_panao raid_helicopter_lobos; do echo "$slk $s.sav $m $sc" >> /tmp/fpsr_jobs.txt; done; done; done; done
cat /tmp/fpsr_jobs.txt | xargs -P 2 -L 1 bash -c 'FPS_SLK=$0 python3 fpsrun.py cand $1 $2 $3 2>&1 | grep -E "FPS|Error|Trace"' > /tmp/fpsr_results.txt
echo DONE >> /tmp/fpsr_results.txt
