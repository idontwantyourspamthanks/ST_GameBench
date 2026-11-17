#!/bin/bash
# master queue after the pass-mode fix: extras per tick, steered state gates, cold boots/floppy/plays, pool sweep
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
unset TINT_SHOW
T=work/tint; R=$T/res
S="python3 $T/steer_int.py"
for m in 8 16 32; do
  $S race_drive X $m 1300 $R/ext_X_$m.json steer=zig mode=pass >> $R/ext_log.txt 2>&1
done
$S race_drive NX 8 1300 $R/ext_NX_8.json steer=zig mode=pass >> $R/ext_log.txt 2>&1
echo DONE_EXT > $R/ext.done
cd $T; L=res/state_log4.txt
run() { echo "== $*" >> $L; timeout 3000 python3 exp_state_int.py "$@" >> $L 2>&1; }
run A ste1m_race_start.sav 8 260 res/st_zig_start_A8.json zig=140
run T ste1m_race_start.sav 8 260 res/st_zig_start_T8.json zig=140
run X ste1m_race_start.sav 16 260 res/st_zig_start_X16.json zig=140
run X ste1m_race_start.sav 32 260 res/st_zig_start_X32.json zig=140
run A ste1m_race_up.sav 8 260 res/st_zig_up_A8.json zig=470
run T ste1m_race_up.sav 8 260 res/st_zig_up_T8.json zig=470
run X ste1m_race_up.sav 16 260 res/st_zig_up_X16.json zig=470
echo ALLDONE >> $L
cd ../..
S="python3 $T/steer_int.py race_start"
$S N 8 520 $R/pool_N.json steer=zig zigk=140 mode=cyc >> $R/pool_log.txt 2>&1
TINT_TAG=_nocar TINT_DROP=tb_car,tb_carph $S F 8 520 $R/pool_nocar.json steer=zig zigk=140 mode=cyc >> $R/pool_log.txt 2>&1
for pe in "8:000da000" "16:000dc000" "24:000de000" "32:000e0000" "44:000e2c00"; do
  kb=${pe%%:*}; v=${pe##*:}
  echo "== pool $kb KB (limit $v)" >> $R/pool_log.txt
  $S F 8 520 $R/pool_p$kb.json steer=zig zigk=140 mode=cyc car poke=bf772=$v >> $R/pool_log.txt 2>&1
done
echo DONE_POOL > $R/pool.done
for c in "ste 1024 1.62 0,16" "ste 4096 1.62 0,16" "megaste 1024 2.06 0,16" "megaste 2048 2.06 0,16" "megaste 4096 2.06 0,16" "st 1024 1.04 0,16" "tt 4096 3.06 0" "falcon 4096 4.04 0"; do
  set -- $c
  echo "=== HD cold $c"; timeout 1500 python3 $T/cold_int.py $1 $2 $3 build/tight_hd tint_$1_$2 $4 2>&1 | grep -v "^$" | cut -c1-520
done > $R/cold_hd.txt 2>&1
for c in "megaste 1024 2.06 16" "megaste 4096 2.06 16" "ste 1024 1.62 16" "ste 4096 1.62 16" "st 1024 1.04 16"; do
  set -- $c
  echo "=== FLOPPY gate $c"; timeout 900 python3 tools/msrfloppy.py gate build/tight_floppy/disk_a.st --disk-b build/tight_floppy/disk_b.st --machine $1 --mem $2 --tos $3 --cpu $4 --name tint_$1_$2 2>&1 | cut -c1-300
done > $R/cold_floppy.txt 2>&1
timeout 900 python3 $T/play5_int.py ste 1024 1.62 build/tight_hd 8 16700 > $R/play5_8.txt 2>&1
timeout 900 python3 $T/play5_int.py ste 1024 1.62 build/tight_hd 16 16700 > $R/play5_16.txt 2>&1
echo DONE_ALL > $R/all.done
