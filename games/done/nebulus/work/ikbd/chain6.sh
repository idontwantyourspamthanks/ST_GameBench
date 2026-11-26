#!/bin/sh
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
while [ ! -f work/ikbd/chain5.done ]; do sleep 3; done
python3 work/ikbd/e_eq.py ni_ikbd_neg > work/ikbd/eq_neg.out 2>&1
rm -f patches/ni_ikbd_neg.nep
echo done > work/ikbd/chain6.done
