#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/liftperf
g() { name=$1; snap=$2; end=$3; en=$4; nl=$5
  python3 seq.py $snap g_${name}_base $end $en - $nl > /tmp/lp/g_${name}_base.out 2>&1
  python3 seq.py $snap g_${name}_lift $end $en np_lift $nl > /tmp/lp/g_${name}_lift.out 2>&1
  python3 cmpseq.py g_${name}_base g_${name}_lift > /tmp/lp/g_${name}.cmp 2>&1
}
g t1ride /tmp/lp/ste_s_t1.sav 24 0 110
g t6ride /tmp/lp/ste_s_t6.sav 24 1 100
g t8ride /tmp/lp/ste_s_t8.sav 24 1 100
g t7long /tmp/lp/ste_s_t7.sav 40 0 150
EV="3:08,40:88,46:08,70:00" g t1walk /tmp/lp/ste_s_t1.sav 0 0 90
EV="3:08,40:88,46:08,70:00" POKES='w $32af1 $81;w $32bf1 $81' g t3walk /tmp/lp/ste_s_t3.sav 0 1 90
echo done > /tmp/lp/gate.done
