#!/bin/sh
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2
while ! grep -q "^done" work/fire/batch4.log; do sleep 10; done
F="python3 work/fire/fire.py"; S=work/snapshots
for v in old_nojag old_jag fix_nojag fix_jag; do
$F g_$v work/snapshots/raid_onfoot_dhafra.sav ste 2048 J 4 --hz 50 --cpu 8 --live build/live/fire_$v
done
for m in J; do
$F a_ste_jeep_$m $S/raid_jeep_dhafra.sav ste 2048 $m 16 --hz 50 --cpu 8
$F b_ste_jeep_$m $S/fire_ste14_jeep.sav ste 1024 $m 16 --hz 50 --cpu 8 --type 1
$F e_ste_jeep_$m $S/fire_ste14fix_jeep.sav ste 1024 $m 16 --hz 50 --cpu 8 --type 1
$F d_ms_jeep_$m $S/fire_ms0_jeep.sav megaste 4096 $m 16 --hz 60 --cpu 16 --type 1
$F c_tt_jeep_$m $S/fire_tt14_jeep.sav tt 4096 $m 16 --hz 60 --cpu 32 --type 1
$F f_tt_jeep_$m $S/fire_tt14fix_jeep.sav tt 4096 $m 16 --hz 60 --cpu 32 --type 1
done
echo done
