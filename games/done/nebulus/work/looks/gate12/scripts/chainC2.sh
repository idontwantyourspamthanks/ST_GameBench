#!/bin/bash
N=/tmp/ng12hd/nb; X=/tmp/ng12hd/x; M=work/core; HD=/tmp/ng12hd/q/hd; L=/tmp/ng12hd/logs/core2; mkdir -p $L; mkdir -p /tmp/ng12hd/q/lp
while [ ! -f /tmp/ng12hd/logs/master.done ]; do sleep 20; done
cd $N; export HOME=/tmp/ng12hd/home PYTHONUNBUFFERED=1 PYTHONPATH=/tmp/ng12hd/sc
step(){ echo "== $1 $(date +%T)" >> $L/steps.txt; }
step e98; python3 $M/e98_g.py > $L/e98.txt 2>&1
step ik; python3 $M/ikg.py snap ste > $L/ik_snap_ste.txt 2>&1; python3 $M/ikg.py sweep ste > $L/ik_sweep_ste.txt 2>&1; python3 $M/ikg.py rand ste 8 7 > $L/ik_rand_ste.txt 2>&1
python3 $M/ikg.py snap megaste > $L/ik_snap_mega.txt 2>&1; python3 $M/ikg.py sweep megaste > $L/ik_sweep_mega.txt 2>&1
step lift; cd $N/$M/lift; python3 mksnap2.py $HD /tmp/ng12hd/q/lp/ste_ship ste 6 > $L/lift_mksnap.txt 2>&1
for i in 1 2; do python3 ride2.py /tmp/ng12hd/q/lp/ste_ship_t6.sav ship_t6_r$i 24 1 ste $HD > $L/lift_ride_r$i.txt 2>&1; python3 ana.py /tmp/ng12hd/q/lp/tr_ship_t6_r$i/log.txt > $L/lift_ana_r$i.txt 2>&1; done
cd $N
step shot; python3 $M/shot/mkledge_g.py > $L/shot_mkledge.txt 2>&1; python3 $M/shot/hat_g.py $N/$M/shot/ledge_ship.sav ship > $L/shot_ship.txt 2>&1
step e206ste; python3 work/editor/e206.py /tmp/ng12hd/wd/e206b_ste ste > $L/e206_ste_rerun.txt 2>&1
step e205ste; python3 work/editor/e205.py /tmp/ng12hd/s/hd /tmp/ng12hd/wd/e205b_ste ste > $L/e205_ste_rerun.txt 2>&1
echo done > $L/done
