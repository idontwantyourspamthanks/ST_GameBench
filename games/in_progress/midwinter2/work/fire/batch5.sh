#!/bin/sh
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2
F="python3 work/fire/fire.py"; S=work/snapshots; m=M
$F c_tt_foot_$m $S/fire_tt14_foot.sav tt 4096 $m 4 --hz 60 --cpu 32 --type 5
$F c_tt_jeep_$m $S/fire_tt14_jeep.sav tt 4096 $m 16 --hz 60 --cpu 32 --type 1
$F f_tt_foot_$m $S/fire_tt14fix_foot.sav tt 4096 $m 4 --hz 60 --cpu 32 --type 5
$F f_tt_jeep_$m $S/fire_tt14fix_jeep.sav tt 4096 $m 16 --hz 60 --cpu 32 --type 1
echo done
