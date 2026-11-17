#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
R=work/speechbar/res; S=work/speechbar
while ! grep -q CYCDONE $R/h2_log.txt 2>/dev/null; do sleep 10; done
L=$R/h3_log.txt
cap() { # scene snap N
  for v in F S; do rm -rf /tmp/sbpix_$1_$v; timeout 1500 python3 $S/cap_sb.py $v $2 8 $3 /tmp/sbpix_$1_$v 40 hold >> $L 2>&1; done
  python3 $S/mask_sb.py /tmp/sbpix_$1_F /tmp/sbpix_$1_S > $R/mask_$1.txt 2>&1
  rm -rf /tmp/sbpix_$1_F /tmp/sbpix_$1_S
}
cap race_start ste1m_race_start.sav 330
cap race_grid ste1m_race_grid.sav 200
cap race_up ste1m_race_up.sav 250
cap race_drive ste1m_race_drive.sav 330
for ctl in "tall b62b4=7e1a" "nowipe b6070=4e714e71"; do
  set -- $ctl
  rm -rf /tmp/sbpix_F /tmp/sbpix_N; timeout 1500 python3 $S/cap_sb.py F ste1m_race_start.sav 8 330 /tmp/sbpix_F 40 hold >> $L 2>&1
  timeout 1500 python3 $S/cap_sb.py S ste1m_race_start.sav 8 330 /tmp/sbpix_N 40 hold $2 >> $L 2>&1
  python3 $S/mask_sb.py /tmp/sbpix_F /tmp/sbpix_N > $R/mask_neg_$1.txt 2>&1
  rm -rf /tmp/sbpix_F /tmp/sbpix_N
done
echo PIXDONE >> $L
rm -f $R/flip_log.txt
timeout 3400 python3 $S/cap_flip_sb.py race_start XS 16 300 $R/flip_XS16.json steer=zig >> $R/flip_log.txt 2>&1
timeout 3400 python3 $S/cap_flip_sb.py race_start XS 32 300 $R/flip_XS32.json steer=zig >> $R/flip_log.txt 2>&1
timeout 3400 python3 $S/cap_flip_sb.py race_start XS 8 300 $R/flip_XS8.json steer=zig >> $R/flip_log.txt 2>&1
timeout 3400 python3 $S/cap_flip_sb.py race_drive XS 16 400 $R/flip_drive_XS16.json steer=zig >> $R/flip_log.txt 2>&1
echo FLIPDONE >> $L
for scene in race_start race_grid; do for v in F S SF; do timeout 900 python3 $S/stage_sb.py $scene $v 8 230 $R/stage_final_${scene}_$v.json >> $R/stage_final_log.txt 2>&1; done; done
echo STAGEDONE >> $L
