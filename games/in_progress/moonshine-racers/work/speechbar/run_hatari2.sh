#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
R=work/speechbar/res; S=work/speechbar
while ! grep -q DONE $R/state_log.txt 2>/dev/null; do sleep 10; done
L=$R/h2_log.txt
cap() { # scene snap N
  for v in F S; do rm -rf /tmp/sbpix_$1_$v; timeout 1500 python3 $S/cap_sb.py $v $2 8 $3 /tmp/sbpix_$1_$v 40 hold >> $L 2>&1; done
  python3 $S/mask_sb.py /tmp/sbpix_$1_F /tmp/sbpix_$1_S > $R/mask_$1.txt 2>&1
  rm -rf /tmp/sbpix_$1_F /tmp/sbpix_$1_S
}
cap race_start ste1m_race_start.sav 330
cap race_grid ste1m_race_grid.sav 200
cap race_up ste1m_race_up.sav 250
cap race_drive ste1m_race_drive.sav 330
# negative controls (race_start): strip one row too tall; no wipe at the message end
for ctl in "tall b62b4=7e1a" "nowipe b6070=4e714e71"; do
  set -- $ctl
  rm -rf /tmp/sbpix_F /tmp/sbpix_N; timeout 1500 python3 $S/cap_sb.py F ste1m_race_start.sav 8 330 /tmp/sbpix_F 40 hold >> $L 2>&1
  timeout 1500 python3 $S/cap_sb.py S ste1m_race_start.sav 8 330 /tmp/sbpix_N 40 hold $2 >> $L 2>&1
  python3 $S/mask_sb.py /tmp/sbpix_F /tmp/sbpix_N > $R/mask_neg_$1.txt 2>&1
  rm -rf /tmp/sbpix_F /tmp/sbpix_N
done
echo PIXDONE >> $L
# extra frames: every flip's strip at 16 MHz and 32 MHz
timeout 3400 python3 $S/cap_flip_sb.py ste1m_race_start.sav XS 16 300 $R/flip_XS16.json steer=zig >> $R/flip_log.txt 2>&1
timeout 3400 python3 $S/cap_flip_sb.py ste1m_race_start.sav XS 32 300 $R/flip_XS32.json steer=zig >> $R/flip_log.txt 2>&1
timeout 3400 python3 $S/cap_flip_sb.py ste1m_race_start.sav XS 8 300 $R/flip_XS8.json steer=zig >> $R/flip_log.txt 2>&1
echo FLIPDONE >> $L
# extras per tick (the user's metric), 2-minute drive with messages at 8 MHz: race_drive zig 1300 passes, X vs XS
for v in X XS; do timeout 3400 python3 $S/cyc_sb.py race_drive $v 8 1300 $R/ext_${v}_8.json steer=zig mode=pass >> $R/ext_log.txt 2>&1; done
echo EXTDONE >> $L
# cycles: F / S / SF
for scene in race_start race_grid; do for v in F S SF; do timeout 1500 python3 $S/cyc_sb.py $scene $v 8 230 $R/cyc_${scene}_$v.json steer=none mode=cyc >> $R/cyc_log.txt 2>&1; done; done
echo CYCDONE >> $L
