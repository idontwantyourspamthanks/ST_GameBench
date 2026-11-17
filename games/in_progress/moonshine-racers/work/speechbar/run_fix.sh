#!/bin/bash
# one Hatari at a time; final build (DATA $BA900)
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
R=work/speechbar/res; S=work/speechbar; L=$R/all_log.txt
true
# ---- state gate (A = stock baselines kept)
run() { echo "== $*" >> $R/state_log.txt; timeout 3000 python3 $S/exp_state_sb.py "$@" >> $R/state_log.txt 2>&1; }
run TS ste1m_race_start.sav 8 260 $R/st_start_TS8.json zig=140
run XS ste1m_race_start.sav 16 260 $R/st_start_XS16.json zig=140
run XS ste1m_race_start.sav 32 260 $R/st_start_XS32.json zig=140
run TS ste1m_race_drive.sav 8 300 $R/st_drive_TS8.json
run XS ste1m_race_drive.sav 16 300 $R/st_drive_XS16.json
echo STATEDONE >> $L
# ---- pixel gate + negative controls
cap() { for v in F S; do rm -rf /tmp/sbpix_$1_$v; timeout 1500 python3 $S/cap_sb.py $v $2 8 $3 /tmp/sbpix_$1_$v 40 hold >> $L 2>&1; done
  python3 $S/mask_sb.py /tmp/sbpix_$1_F /tmp/sbpix_$1_S > $R/mask_$1.txt 2>&1; rm -rf /tmp/sbpix_$1_F /tmp/sbpix_$1_S; }
cap race_start ste1m_race_start.sav 330
cap race_grid ste1m_race_grid.sav 200
cap race_up ste1m_race_up.sav 250
cap race_drive ste1m_race_drive.sav 330
for ctl in "tall b6306=7e1a" "nowipe b6074=4e714e71"; do set -- $ctl
  rm -rf /tmp/sbpix_F /tmp/sbpix_N; timeout 1500 python3 $S/cap_sb.py F ste1m_race_start.sav 8 330 /tmp/sbpix_F 40 hold >> $L 2>&1
  timeout 1500 python3 $S/cap_sb.py S ste1m_race_start.sav 8 330 /tmp/sbpix_N 40 hold $2 >> $L 2>&1
  python3 $S/mask_sb.py /tmp/sbpix_F /tmp/sbpix_N > $R/mask_neg_$1.txt 2>&1; rm -rf /tmp/sbpix_F /tmp/sbpix_N; done
echo PIXDONE >> $L
# ---- flip captures (extras)
timeout 3400 python3 $S/cap_flip_sb.py race_start XS 16 300 $R/flip_XS16.json steer=zig >> $R/flip_log.txt 2>&1
timeout 3400 python3 $S/cap_flip_sb.py race_start XS 32 300 $R/flip_XS32.json steer=zig >> $R/flip_log.txt 2>&1
timeout 3400 python3 $S/cap_flip_sb.py race_start XS 8 300 $R/flip_XS8.json steer=zig >> $R/flip_log.txt 2>&1
timeout 3400 python3 $S/cap_flip_sb.py race_drive XS 16 400 $R/flip_drive_XS16.json steer=zig >> $R/flip_log.txt 2>&1
echo FLIPDONE >> $L
# ---- cold boots
CL=$R/cold_log.txt
for cfg in "ste 1024 1.62 ste1m" "ste 4096 1.62 ste4m" "megaste 1024 2.06 mste1m"; do set -- $cfg
  echo "=== sb HD cold $1 $2 $3" >> $CL; timeout 2400 python3 $S/cold_sb.py $1 $2 $3 build/sb_hd $4 0,16 >> $CL 2>&1; done
echo FIXDONE >> $L
