cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
O=/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebGateCore/out
while [ ! -f $O/qD.done ]; do sleep 5; done
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebGateCore/lift
echo "== lift live $(date +%T)"
LIVE="np_lift" python3 ride2.py /tmp/lp/ste_s_t6.sav live_lift 24 1 ste /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/originals/NEBULGX > $O/lift_ride_live1.txt 2>&1
python3 ana.py /tmp/gcore_lp/tr_live_lift/log.txt > $O/lift_ana_live_lift.txt 2>&1
LIVE="np_lift ni_ikbd ni_jump ni_latch ni_shoot ni_turn np_shot nt_trainers cr_credit" python3 ride2.py /tmp/lp/ste_s_t6.sav live_all 24 1 ste /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/originals/NEBULGX > $O/lift_ride_live2.txt 2>&1
python3 ana.py /tmp/gcore_lp/tr_live_all/log.txt > $O/lift_ana_live_all.txt 2>&1
echo done > $O/qE.done
