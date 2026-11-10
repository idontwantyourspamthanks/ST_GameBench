#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/midwinter2/work/vehicles_p3b
: > /tmp/fps_jobs.txt
SN="raid_onfoot_dhafra raid_jeep_dhafra raid_truck_aledo raid_bus_galva raid_speedboat_iquitos raid_crawler_panao raid_submarine_jebba raid_ship_bourem raid_biplane_maracay raid_helicopter_lobos raid_balloon_corozal raid_parachute_calabar raid_flyingboat_vicenza raid_hovercraft_thar raid_swimming_vitoria"
for m in 8 16; do for s in $SN; do for c in v12 cand; do echo "$c $s.sav $m stand" >> /tmp/fps_jobs.txt; done; done; done
for m in 8 16; do for s in raid_onfoot_dhafra raid_jeep_dhafra raid_speedboat_iquitos raid_biplane_maracay raid_helicopter_lobos; do for c in v12 cand; do echo "$c $s.sav $m move" >> /tmp/fps_jobs.txt; done; done; done
cat /tmp/fps_jobs.txt | xargs -P ${NP:-1} -L 1 bash -c 'python3 fpsrun.py $0 $1 $2 $3 2>&1 | grep -E "FPS|Error|Trace"' > /tmp/fps_results.txt
echo DONE >> /tmp/fps_results.txt
