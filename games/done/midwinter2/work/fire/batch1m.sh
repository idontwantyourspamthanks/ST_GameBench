#!/bin/sh
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2
F="python3 work/fire/fire.py"
S=work/snapshots
m=M
$F a_ste_foot_$m $S/raid_onfoot_dhafra.sav ste 2048 $m 4 --hz 50 --cpu 8
$F a_ste_jeep_$m $S/raid_jeep_dhafra.sav ste 2048 $m 16 --hz 50 --cpu 8
$F b_ste_foot_$m $S/fire_ste14_foot.sav ste 1024 $m 4 --hz 50 --cpu 8 --type 5
$F b_ste_jeep_$m $S/fire_ste14_jeep.sav ste 1024 $m 16 --hz 50 --cpu 8 --type 1
$F d_ms_foot_$m $S/fire_ms0_foot.sav megaste 4096 $m 4 --hz 60 --cpu 16 --type 5
$F d_ms_jeep_$m $S/fire_ms0_jeep.sav megaste 4096 $m 16 --hz 60 --cpu 16 --type 1
$F c_tt_foot_$m $S/fire_tt14_foot.sav tt 4096 $m 4 --hz 60 --cpu 32 --type 5
$F c_tt_jeep_$m $S/fire_tt14_jeep.sav tt 4096 $m 16 --hz 60 --cpu 32 --type 1
echo done
