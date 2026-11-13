#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2/work/scratch/disks
A=/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2/alt/ST
run(){ timeout 900 python3 matrix.py "$@" >> chainB.log 2>&1; }
: > chainB.log
run Elite.st elite_2m 2048 elite
run "$A/Populous II (1992)(Bullfrog)[cr Superior][1 MB].st" sup_2m 2048 sup
run Elite.st elite_512 512 elite
run "$A/Populous II (1992)(Bullfrog)[cr Superior][1 MB].st" sup_512 512 sup
echo CHAIN-DONE >> chainB.log
