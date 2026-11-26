#!/bin/sh
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
while pgrep -f "chain1.sh" > /dev/null; do sleep 2; done
python3 work/ikbd/t1.py orig > work/ikbd/t1_orig.out 2>&1
python3 work/ikbd/r6.py patched > work/ikbd/r6_patched.out 2>&1
python3 work/ikbd/j1.py patched all 1 > work/ikbd/j1_all.out 2>&1
python3 work/ikbd/j1.py patched rs 2 > work/ikbd/j1_rs.out 2>&1
python3 work/ikbd/r7.py orig 0.5 > work/ikbd/r7_orig.out 2>&1
python3 work/ikbd/r7.py fixed 0.5 > work/ikbd/r7_fixed.out 2>&1
python3 work/ikbd/e_eq.py ni_ikbd > work/ikbd/eq_ikbd.out 2>&1
python3 work/input/gate_boot.py work/ikbd/build/fixed ste ik1 > work/ikbd/gate_ste.out 2>&1
python3 work/input/gate_boot.py work/ikbd/build/fixed megaste ik2 > work/ikbd/gate_megaste.out 2>&1
python3 work/ikbd/t30.py fixed t30 0.05 30 > work/ikbd/t30.out 2>&1
echo CHAIN2 DONE > work/ikbd/chain2.done
