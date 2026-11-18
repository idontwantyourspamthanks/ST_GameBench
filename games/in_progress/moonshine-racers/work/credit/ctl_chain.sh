#!/bin/sh
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
run() { timeout 1100 python3 work/credit/state_cold.py hd build/$2 work/credit/st_ctl_$1.json 150 > work/credit/st_ctl_$1.log 2>&1; }
run stock_a credit_curbase_hd
run real_a credit_hd
for N in 0 500 1500 3000 6000 9000 12000 20000 30000; do run delay_$N tdelay_$N; done
run stock_b credit_curbase_hd
run real_b credit_hd
run stock_c credit_curbase_hd
run real_c credit_hd
echo done > work/credit/ctl_done.txt
