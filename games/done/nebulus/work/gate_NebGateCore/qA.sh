cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
O=work/gate_NebGateCore/out
SH=/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebGateCore/unz/NEBULUS
echo "== e98 $(date +%T)"; python3 work/gate_NebGateCore/e98_g.py > $O/e98.txt 2>&1
echo "== orig $(date +%T)"; python3 work/gate_NebGateCore/orig_sanity.py > $O/orig.txt 2>&1
echo "== ik snap ste $(date +%T)"; python3 work/gate_NebGateCore/ikg.py snap ste > $O/ik_snap_ste.txt 2>&1
python3 work/gate_NebGateCore/ikg.py sweep ste > $O/ik_sweep_ste.txt 2>&1
python3 work/gate_NebGateCore/ikg.py rand ste 12 7 > $O/ik_rand_ste.txt 2>&1
python3 work/gate_NebGateCore/ikg.py ctl > $O/ik_ctl.txt 2>&1
echo "== lift $(date +%T)"
cd work/gate_NebGateCore/lift
python3 mksnap2.py $SH /tmp/gcore_lp/ste_ship ste 6 > $O/../out/lift_mksnap.txt 2>&1
python3 ride2.py /tmp/gcore_lp/ste_ship_t6.sav ship_t6 24 1 ste $SH > $O/lift_ride_ship.txt 2>&1
python3 ana.py /tmp/gcore_lp/tr_ship_t6/log.txt > $O/lift_ana_ship.txt 2>&1
python3 ride2.py /tmp/lp/ste_s_t6.sav ctl_t6 24 1 ste /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/originals/NEBULGX > $O/lift_ride_ctl.txt 2>&1
python3 ana.py /tmp/gcore_lp/tr_ctl_t6/log.txt > $O/lift_ana_ctl.txt 2>&1
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
echo "== shot $(date +%T)"
python3 work/gate_NebGateCore/shot/mkledge_g.py > $O/shot_mkledge.txt 2>&1
python3 work/gate_NebGateCore/shot/hat_g.py /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebGateCore/shot/ledge_ship.sav ship > $O/shot_ship.txt 2>&1
python3 work/gate_NebGateCore/shot/hat_g.py /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/shotmiss/ledge.sav stockctl > $O/shot_ctl.txt 2>&1
echo done > $O/qA.done
