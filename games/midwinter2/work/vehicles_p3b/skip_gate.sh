#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/midwinter2/work/vehicles_p3b
DISP=$(cat /tmp/disp_set.txt)
TK=tick_vbl,tick_head,tick_render
SK=p7_skip_render,p7_skip_enter,p7_skip_gate,p7_skip_scn,p7_skip_wv1,p7_skip_wv2,p7_skip_wv3
: > /tmp/vg/skip1.txt
for s in raid_onfoot_dhafra raid_jeep_dhafra raid_truck_aledo raid_bus_galva raid_speedboat_iquitos raid_crawler_panao raid_submarine_jebba raid_ship_bourem raid_biplane_maracay raid_helicopter_lobos raid_balloon_corozal raid_parachute_calabar raid_flyingboat_vicenza raid_hovercraft_thar raid_swimming_vitoria; do
  for f in 10 40; do python3 ab2.py $s.sav $f $TK,$DISP $TK,$DISP,$SK --mhz 16 2>&1 | grep RESULT >> /tmp/vg/skip1.txt; done
done
echo DONE >> /tmp/vg/skip1.txt
