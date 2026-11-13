#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2/work/scratch/disks
A=/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2/alt/ST
run(){ timeout 900 python3 matrix.py "$@" >> chain.log 2>&1; }
: > chain.log
run ICS91.st ics91_1m 1024 ics
run ICS91.st ics91_2m 2048 ics
run Vmax.st vmax_1m 1024 ics
run Vmax.st vmax_2m 2048 ics
run "ICS[a].st" icsa_1m 1024 ics
run Illegal.st ill_512 512 ics
run Illegal.st ill_1m 1024 ics
run Elite.st elite_2m 2048 elite
run Elite.st elite_512 512 elite
run "$A/Populous II (1992)(Bullfrog)[cr Superior][1 MB].st" sup_2m 2048 sup
run "$A/Populous II (1992)(Bullfrog)[cr Superior][1 MB].st" sup_512 512 sup
echo CHAIN-DONE >> chain.log
