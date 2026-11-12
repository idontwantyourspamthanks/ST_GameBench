#!/bin/sh
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2
F="python3 work/fire/fire.py"; S=work/snapshots; m=M
$F d_ms_foot_$m $S/fire_ms0_foot.sav megaste 4096 $m 4 --hz 60 --cpu 16 --type 5
$F d_ms_jeep_$m $S/fire_ms0_jeep.sav megaste 4096 $m 16 --hz 60 --cpu 16 --type 1
echo done
