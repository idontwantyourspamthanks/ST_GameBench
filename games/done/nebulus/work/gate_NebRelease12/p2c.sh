#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus; L=work/gate_NebRelease12/logs; B=/tmp/r12; O=/tmp/looksgate/ne/odd; export PYTHONUNBUFFERED=1
while [ ! -f $L/p2b.done ]; do sleep 20; done
for i in 1 2 3; do for v in v12:$B/s/hd/NEBULUS v111:$B/s/hd111/NEBULUS; do n=${v%%:*}; d=${v#*:}
 echo "== $n run$i $(date +%T)" >> $L/p2c_steps.txt
 CAPDIR=work/gate_NebRelease12/cap_${n}_$i python3 work/editor/e180cap.py $d $B/wd180c_${n}_$i ste $O/looks.ovl --disk > $L/looks_walk_${n}_$i.log 2>&1
done; done
echo done > $L/p2c.done
for e in 3 4; do echo "== eye$e $(date +%T)" >> $L/p2c_steps.txt; NOE=1 DELAY=2 python3 work/looks/run_look.py $B/hd_eye$e $B/r/eye${e}_ste 1 camp ste > $L/eye${e}_ste.log 2>&1; done
echo done > $L/p2d.done
