cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
O=/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebGateCore/out
while [ ! -f $O/qG.done ]; do sleep 5; done
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebGateCore/lift
for v in noik nolatch notrain liftonly; do
echo "== lift diag $v $(date +%T)"
G=/tmp/nebgc_$v; case $v in notrain|liftonly) G=/tmp/nebgc_stock_$v;; esac
python3 mksnap2.py /tmp/nebgc_$v /tmp/gcore_lp/ste_$v ste 6 > $O/lift_mksnap_$v.txt 2>&1
python3 ride2.py /tmp/gcore_lp/ste_${v}_t6.sav diag_$v 24 1 ste $G > $O/lift_ride_$v.txt 2>&1
python3 ana.py /tmp/gcore_lp/tr_diag_$v/log.txt > $O/lift_ana_$v.txt 2>&1
done
echo done > $O/qH.done
