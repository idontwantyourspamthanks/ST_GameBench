#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2/work/scratch/disks
A=/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2/alt/ST
run(){ timeout 1200 python3 matrix.py "$@" >> chainD.log 2>&1; }
: > chainD.log
run Elite.st elite_1m 1024 elite
run Elite.st elite_2m 2048 elite
run "$A/Populous II (1992)(Bullfrog)[cr Superior][1 MB].st" sup_1m 1024 sup
echo CHAIN-DONE >> chainD.log
