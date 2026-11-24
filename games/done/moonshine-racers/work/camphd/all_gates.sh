#!/bin/bash
# the full HD campaign gate chain on the b4 build (one Hatari at a time); logs log_*.txt
cd "$(dirname "$0")"
while pgrep -f boot8.sh >/dev/null; do sleep 10; done
G="./env.sh python3 gate.py"
$G drivea --machine ste --mem 2048 --tag drA_ste2m > log_drA_ste2m.txt 2>&1
$G errors --machine ste --mem 2048 --tag err_ste2m > log_err_ste2m.txt 2>&1
$G timeout --machine ste --mem 2048 --tag to_ste2m > log_to_ste2m.txt 2>&1
for c in "ste 4096" "megaste 2048" "megaste 4096" "st 2048" "st 4096" "megast 2048" "megast 4096"; do
  set -- $c; n=$1$2
  $G finish --machine $1 --mem $2 --camp c1 --tag fin_$n > log_fin_$n.txt 2>&1
done
$G drivea --machine megaste --mem 4096 --tag drA_mste4m > log_drA_mste4m.txt 2>&1
$G drivea --machine st --mem 2048 --tag drA_st2m > log_drA_st2m.txt 2>&1
$G stock --machine ste --mem 4096 --minutes 10 --tag stock_ste4m > log_stock_ste4m.txt 2>&1
for m in ste st; do ./env.sh python3 ab1mb.py --machine $m > log_ab1m_$m.txt 2>&1; done
./env.sh python3 probe_type.py --game ../camphd/b4 --machine tt --mem 4096 --tos 3.06 > log_probe_tt.txt 2>&1
./env.sh python3 probe_type.py --game ../camphd/b4 --machine falcon --mem 4096 --tos 4.04 > log_probe_falcon.txt 2>&1
echo ALLDONE > log_alldone.txt
