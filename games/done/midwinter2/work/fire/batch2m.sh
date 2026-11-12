#!/bin/sh
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2
F="python3 work/fire/fire.py"
S=work/snapshots
m=M
$F e_ste_foot_$m $S/fire_ste14fix_foot.sav ste 1024 $m 4 --hz 50 --cpu 8 --type 5
$F e_ste_jeep_$m $S/fire_ste14fix_jeep.sav ste 1024 $m 16 --hz 50 --cpu 8 --type 1
$F f_tt_foot_$m $S/fire_tt14fix_foot.sav tt 4096 $m 4 --hz 60 --cpu 32 --type 5
$F f_tt_jeep_$m $S/fire_tt14fix_jeep.sav tt 4096 $m 16 --hz 60 --cpu 32 --type 1
echo done
