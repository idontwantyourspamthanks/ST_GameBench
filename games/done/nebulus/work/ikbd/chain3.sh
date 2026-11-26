#!/bin/sh
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
while [ ! -f work/ikbd/chain2.done ]; do sleep 3; done
python3 work/ikbd/e1.py patched > work/ikbd/e1_patched.out 2>&1
python3 work/ikbd/e1.py fixed > work/ikbd/e1_fixed.out 2>&1
python3 work/ikbd/r8.py orig > work/ikbd/r8_orig.out 2>&1
python3 work/ikbd/r8.py patched > work/ikbd/r8_patched.out 2>&1
echo CHAIN3 DONE > work/ikbd/chain3.done
