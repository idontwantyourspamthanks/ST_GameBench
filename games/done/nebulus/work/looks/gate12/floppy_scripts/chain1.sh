#!/bin/bash
export HOME=/tmp/ng12fl/home
cd /tmp/ng12fl/s
G=/tmp/ng12fl/game.st; C=/tmp/ng12fl/campaign_disk.st; O=/tmp/ng12fl/out
ODD=$(ls /tmp/ng12fl/ne/odd/*.ovl | tr '\n' ' ')
step(){ echo "== $1 $(date +%T)" >> $O/chain1.log; }
step fge_ste;  python3 fge.py $G /tmp/ng12fl/w_fge_ste ste fuzzsubset > $O/fge_ste.txt 2>&1
step fge2_ste; python3 fge2.py $G /tmp/ng12fl/w_fge2_ste ste > $O/fge2_ste.txt 2>&1
step f161_ste; python3 f161_nfe.py $G /tmp/ng12fl/w_f161_ste ste > $O/f161_ste.txt 2>&1
step fl_look_ste; python3 fl_look.py $G /tmp/ng12fl/w_look_ste /tmp/ng12fl/ne/odd/looks.ovl /tmp/ng12fl/ref/looks15_ste 0,4,9,12,13,14 > $O/fl_look_ste.txt 2>&1
step fo180_ste; python3 fo180.py $G /tmp/ng12fl/w_fo_ste ste $ODD --quick > $O/fo180_ste.txt 2>&1
step fl_ui_mega; python3 fl_ui.py $G /tmp/ng12fl/w_ui_mega /tmp/ng12fl/ref/base8_ste megaste > $O/fl_ui_mega.txt 2>&1
step rt_mega; python3 rt.py $G /tmp/ng12fl/w_rt_mega $C megaste > $O/rt_mega.txt 2>&1
step fge_mega; python3 fge.py $G /tmp/ng12fl/w_fge_mega megaste fuzzsubset > $O/fge_mega.txt 2>&1
step fge2_mega; python3 fge2.py $G /tmp/ng12fl/w_fge2_mega megaste > $O/fge2_mega.txt 2>&1
step f161_mega; python3 f161_nfe.py $G /tmp/ng12fl/w_f161_mega megaste skipfuzz > $O/f161_mega.txt 2>&1
step fo180_mega; python3 fo180.py $G /tmp/ng12fl/w_fo_mega megaste $ODD --quick > $O/fo180_mega.txt 2>&1
step fl_look_mega; MACH=megaste python3 fl_look.py $G /tmp/ng12fl/w_look_mega /tmp/ng12fl/ne/odd/looks.ovl /tmp/ng12fl/ref/looks15_ste 0,4,9 > $O/fl_look_mega.txt 2>&1
step fl_ui_mega16; CPU16=1 python3 fl_ui.py $G /tmp/ng12fl/w_ui_mega16 /tmp/ng12fl/ref/base8_ste megaste > $O/fl_ui_mega16.txt 2>&1
step rt_mega16; CPU16=1 python3 rt.py $G /tmp/ng12fl/w_rt_mega16 $C megaste > $O/rt_mega16.txt 2>&1
step fl_ui_ste16; CPU16=1 python3 fl_ui.py $G /tmp/ng12fl/w_ui_ste16 /tmp/ng12fl/ref/base8_ste ste > $O/fl_ui_ste16.txt 2>&1
step rt_ste16; CPU16=1 python3 rt.py $G /tmp/ng12fl/w_rt_ste16 $C ste > $O/rt_ste16.txt 2>&1
step done
