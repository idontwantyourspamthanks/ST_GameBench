#!/bin/sh
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
while [ ! -f work/ikbd/chain3.done ]; do sleep 3; done
sleep 20
while pgrep -f "t30.py fixed t30b" > /dev/null; do sleep 3; done
python3 work/ikbd/e1b.py patched > work/ikbd/e1b_patched.out 2>&1
python3 work/ikbd/e1b.py fixed > work/ikbd/e1b_fixed.out 2>&1
echo done > work/ikbd/chain4.done
