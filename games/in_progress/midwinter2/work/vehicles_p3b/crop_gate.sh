#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/vehicles_p3b
DISP=$(cat /tmp/disp_set.txt)
NOPFX=$(echo $DISP | tr ',' '\n' | grep -v "p4_hud_pfx" | tr '\n' ',' | sed 's/,$//')
TK=tick_vbl,tick_head,tick_render
CR=p4_hud_crop_clip_t,p4_hud_crop_fill_t,p4_hud_crop_replay_t
: > /tmp/vg/crop1.txt
for s in raid_jeep_dhafra raid_truck_aledo raid_bus_galva raid_onfoot_dhafra raid_speedboat_iquitos raid_crawler_panao raid_submarine_jebba raid_ship_bourem raid_biplane_maracay raid_helicopter_lobos raid_balloon_corozal raid_parachute_calabar raid_flyingboat_vicenza raid_hovercraft_thar raid_swimming_vitoria; do
  python3 ab2.py $s.sav 10 $TK,$DISP $TK,$NOPFX,$CR --mhz 16 2>&1 | grep RESULT >> /tmp/vg/crop1.txt
done
echo DONE >> /tmp/vg/crop1.txt
