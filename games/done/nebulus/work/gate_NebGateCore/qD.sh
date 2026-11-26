cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
O=/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebGateCore/out
SH=/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebGateCore/unz/NEBULUS
while [ ! -f $O/qC.done ]; do sleep 5; done
echo "== ik ste $(date +%T)"
python3 work/gate_NebGateCore/ikg.py snap ste > $O/ik_snap_ste.txt 2>&1
rm -f work/gate_NebGateCore/out/sweep_ste.jsonl work/gate_NebGateCore/out/rand_ste.jsonl work/gate_NebGateCore/out/ctl_ste.jsonl
python3 work/gate_NebGateCore/ikg.py sweep ste > $O/ik_sweep_ste.txt 2>&1
python3 work/gate_NebGateCore/ikg.py rand ste 12 7 > $O/ik_rand_ste.txt 2>&1
python3 work/gate_NebGateCore/ikg.py ctl ste > $O/ik_ctl.txt 2>&1
echo "== lift reruns $(date +%T)"
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebGateCore/lift
for i in 2 3; do
python3 ride2.py /tmp/gcore_lp/ste_ship_t6.sav ship_t6_r$i 24 1 ste $SH > $O/lift_ride_ship_r$i.txt 2>&1
python3 ana.py /tmp/gcore_lp/tr_ship_t6_r$i/log.txt > $O/lift_ana_ship_r$i.txt 2>&1
done
echo done > $O/qD.done
