#!/bin/bash
# fps of the candidate set (defaults + p3cp_head + p3c_sim + p7_skip_render) over 1000 VBL after a live apply; 15 Raids snapshots standing, 5 moving; 8/16/32 MHz.  NP parallel Hatari (default 2).
cd /home/ryan/Code/AtariST/gamebench/games/midwinter2/work/vehicles_p3b
: > /tmp/fpsc_jobs.txt
SN="raid_onfoot_dhafra raid_jeep_dhafra raid_truck_aledo raid_bus_galva raid_speedboat_iquitos raid_crawler_panao raid_submarine_jebba raid_ship_bourem raid_biplane_maracay raid_helicopter_lobos raid_balloon_corozal raid_parachute_calabar raid_flyingboat_vicenza raid_hovercraft_thar raid_swimming_vitoria"
for m in 8 16 32; do for s in $SN; do echo "cand $s.sav $m stand" >> /tmp/fpsc_jobs.txt; done; done
for m in 8 16 32; do for s in raid_onfoot_dhafra raid_jeep_dhafra raid_speedboat_iquitos raid_biplane_maracay raid_helicopter_lobos; do echo "cand $s.sav $m move" >> /tmp/fpsc_jobs.txt; done; done
cat /tmp/fpsc_jobs.txt | xargs -P ${NP:-2} -L 1 bash -c 'python3 fpsrun.py $0 $1 $2 $3 2>&1 | grep -E "FPS|Error|Trace"' > /tmp/fpsc_results.txt
echo DONE >> /tmp/fpsc_results.txt
