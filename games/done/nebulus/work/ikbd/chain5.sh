#!/bin/sh
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
while [ ! -f work/ikbd/chain4.done ]; do sleep 3; done
python3 work/ikbd/r8.py orig > work/ikbd/r8_orig.out 2>&1
echo done > work/ikbd/chain5.done
