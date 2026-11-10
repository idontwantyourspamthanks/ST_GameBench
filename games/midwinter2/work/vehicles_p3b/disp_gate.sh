#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/midwinter2/work/vehicles_p3b
SET=$(cat /tmp/disp_set.txt)
: > /tmp/vg/disp1.txt
for s in raid_jeep_dhafra raid_truck_aledo raid_bus_galva raid_onfoot_dhafra raid_speedboat_iquitos raid_crawler_panao raid_submarine_jebba raid_ship_bourem raid_biplane_maracay raid_helicopter_lobos raid_balloon_corozal raid_parachute_calabar raid_flyingboat_vicenza raid_hovercraft_thar raid_swimming_vitoria; do
  for f in 10 40; do python3 ab2.py $s.sav $f none "$SET" 2>&1 | grep RESULT >> /tmp/vg/disp1.txt; done
done
echo DONE >> /tmp/vg/disp1.txt
