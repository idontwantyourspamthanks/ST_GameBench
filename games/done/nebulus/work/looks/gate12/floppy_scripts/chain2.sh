#!/bin/bash
export HOME=/tmp/ng12fl/home
while pgrep -f chain1.sh >/dev/null; do sleep 20; done
cd /tmp/ng12fl/s
G=/tmp/ng12fl/game.st; C=/tmp/ng12fl/campaign_disk.st; O=/tmp/ng12fl/out
OLD=/tmp/ng12fl/z/NEBULUS_floppy/Nebulus_game_disk.st
step(){ echo "== $1 $(date +%T)" >> $O/chain2.log; }
step fl_look_ste; python3 fl_look.py $G /tmp/ng12fl/w_look_ste2 x /tmp/ng12fl/ref/looks15_ste 0,4,9,12,13,14 > $O/fl_look_ste2.txt 2>&1
step f161_ste; python3 f161_nfe.py $G /tmp/ng12fl/w_f161_ste2 ste > $O/f161_ste2.txt 2>&1
step mfp_new; python3 mfp.py $G ste /tmp/ng12fl/w_mfp1 > $O/mfp_new.txt 2>&1
step mfp_old; python3 mfp.py $OLD ste /tmp/ng12fl/w_mfp2 > $O/mfp_old.txt 2>&1
step docs2; python3 docs2.py $G /tmp/ng12fl/w_docs $C ste > $O/docs2.txt 2>&1
step done
