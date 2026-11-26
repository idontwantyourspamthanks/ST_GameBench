#!/bin/bash
N=/tmp/ng12hd/nb; M=work/core; L=/tmp/ng12hd/logs/core3; mkdir -p $L
while [ ! -f /tmp/ng12hd/logs/core2/done ]; do sleep 20; done
cd $N; export HOME=/tmp/ng12hd/home PYTHONUNBUFFERED=1 PYTHONPATH=/tmp/ng12hd/sc
python3 $M/ikg.py snap megaste > $L/ik_snap_mega.txt 2>&1; python3 $M/ikg.py sweep megaste > $L/ik_sweep_mega.txt 2>&1
python3 $M/shot/hat_g.py $N/$M/shot/ledge_ship.sav ship > $L/shot_ship.txt 2>&1
echo done > $L/done
