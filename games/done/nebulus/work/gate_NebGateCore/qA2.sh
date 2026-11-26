cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
O=/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebGateCore/out
SH=/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebGateCore/unz/NEBULUS
while [ ! -f $O/qA.done ]; do sleep 5; done
echo "== ik ste $(date +%T)"
python3 work/gate_NebGateCore/ikg.py sweep ste > $O/ik_sweep_ste.txt 2>&1
python3 work/gate_NebGateCore/ikg.py rand ste 12 7 > $O/ik_rand_ste.txt 2>&1
python3 work/gate_NebGateCore/ikg.py ctl > $O/ik_ctl.txt 2>&1
echo "== lift $(date +%T)"
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebGateCore/lift
python3 mksnap2.py $SH /tmp/gcore_lp/ste_ship ste 6 > $O/lift_mksnap.txt 2>&1
python3 ride2.py /tmp/gcore_lp/ste_ship_t6.sav ship_t6 24 1 ste $SH > $O/lift_ride_ship.txt 2>&1
python3 ana.py /tmp/gcore_lp/tr_ship_t6/log.txt > $O/lift_ana_ship.txt 2>&1
python3 ride2.py /tmp/lp/ste_s_t6.sav ctl_t6 24 1 ste /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/originals/NEBULGX > $O/lift_ride_ctl.txt 2>&1
python3 ana.py /tmp/gcore_lp/tr_ctl_t6/log.txt > $O/lift_ana_ctl.txt 2>&1
echo done > $O/qA2.done
