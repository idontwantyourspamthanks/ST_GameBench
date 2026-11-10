#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/midwinter2/work/vehicles_p3b
: > /tmp/vg/bis.txt
P4=p4_grid,p4_proj_axis,p4_proj_cols,p4_proj_div,p4_walk,p4_walk_c4,p4_walk_ret,p4_walk_tab
PFX=p4_hud_pfx_fill,p4_hud_pfx_replay,p4_hud_pfx_ymin,p4_hud_reset
CELL=p7_cell_cull,p7_cell_pre
CK=p7_ck_enter,p7_ck_exit,p7_ck_obj,p7_ck_poly,p7_ck_tab
for s in raid_ship_bourem raid_biplane_maracay; do
  for nm in P4 PFX CELL "PFX,CK" ; do
    eval "set=\$$(echo $nm | sed 's/,/,\$/g')"
    echo "$s $nm" >> /tmp/vg/bis.txt
    python3 ab2.py $s.sav 10 none "$set" 2>&1 | grep RESULT >> /tmp/vg/bis.txt
  done
done
echo DONE >> /tmp/vg/bis.txt
