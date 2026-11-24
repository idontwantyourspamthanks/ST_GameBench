#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/campfloppy
R=./run_env.sh
$R python3 e5.py vblclk --only mid-read > logs/q1_e5vbl.out 2>&1
$R python3 e2.py max_A --camp disk/max720.st --trk disk/max.trk --key A --noride > logs/q1_max.out 2>&1
$R python3 e2.py stock_B --camp disk/stock720.st --trk disk/stock.trk --key B --where B --noride > logs/q1_stockB.out 2>&1
$R python3 e2.py twodrive --camp disk/stock720.st --trk disk/stock.trk --key A --where A --startb $PWD/build/disk_b.st > logs/q1_twodrive.out 2>&1
$R python3 e2.py mste4m --camp disk/stock720.st --trk disk/stock.trk --key A --machine megaste --mem 4096 > logs/q1_mste4m.out 2>&1
$R python3 e3_ram.py ste2m --machine ste --mem 2048 > logs/q1_e3_ste2m.out 2>&1
$R python3 e3_ram.py ste4m --machine ste --mem 4096 > logs/q1_e3_ste4m.out 2>&1
$R python3 e3_ram.py mste2m --machine megaste --mem 2048 > logs/q1_e3_mste2m.out 2>&1
echo QUEUE DONE
