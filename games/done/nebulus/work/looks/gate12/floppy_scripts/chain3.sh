#!/bin/bash
export HOME=/tmp/ng12fl/home
while pgrep -f chain2.sh >/dev/null; do sleep 20; done
cd /tmp/ng12fl/s
G=/tmp/ng12fl/game.st; O=/tmp/ng12fl/out
step(){ echo "== $1 $(date +%T)" >> $O/chain3.log; }
step f161_ste; python3 f161_nfe.py $G /tmp/ng12fl/w_f161_ste3 ste > $O/f161_ste3.txt 2>&1
step fl_look_ste; python3 fl_look.py $G /tmp/ng12fl/w_look_ste3 x /tmp/ng12fl/ref/base8_ste 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14 > $O/fl_look_ste3.txt 2>&1
step f161_mega; python3 f161_nfe.py $G /tmp/ng12fl/w_f161_mega3 megaste skipfuzz > $O/f161_mega3.txt 2>&1
step fl_look_mega; MACH=megaste python3 fl_look.py $G /tmp/ng12fl/w_look_mega3 x /tmp/ng12fl/ref/base8_ste 0,4,9,12,13,14 > $O/fl_look_mega3.txt 2>&1
step done
