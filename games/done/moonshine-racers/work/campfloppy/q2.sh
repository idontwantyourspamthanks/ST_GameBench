#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/campfloppy
R=./run_env.sh
$R python3 e6_gate.py ste1m_pub --build $PWD/build --machine ste --mem 1024 > logs/q2_e6_pub1m.out 2>&1
$R python3 e6_gate.py ste1m --machine ste --mem 1024 --f10 > logs/q2_e6_ste1m.out 2>&1
$R python3 e6_gate.py ste2m --machine ste --mem 2048 --f10 > logs/q2_e6_ste2m.out 2>&1
$R python3 e6_gate.py ste4m --machine ste --mem 4096 --f10 > logs/q2_e6_ste4m.out 2>&1
$R python3 e6_gate.py mste2m --machine megaste --mem 2048 --f10 > logs/q2_e6_mste2m.out 2>&1
$R python3 e6_gate.py st4m --machine st --mem 4096 --f10 > logs/q2_e6_st4m.out 2>&1
$R python3 e6_gate.py st1m --machine st --mem 1024 --f10 > logs/q2_e6_st1m.out 2>&1
$R python3 e8_reads.py > logs/q2_e8.out 2>&1
$R python3 e5b.py retry > logs/q2_e5b.out 2>&1
$R python3 e9_integ.py base5_t0 --camp disk/camp5_720.st --track 0 --ring lev5 --base 5 --len 18000 > logs/q2_e9_t0.out 2>&1
$R python3 e9_integ.py edit_t1 --camp disk/camp5_720.st --track 1 --ring edit1 --base 0 --len 19472 > logs/q2_e9_t1.out 2>&1
echo QUEUE2 DONE
