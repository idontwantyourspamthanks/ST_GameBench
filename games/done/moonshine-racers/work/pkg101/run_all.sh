#!/bin/bash
cd /tmp/msr101
P="python3 gate.py"
R1=/tmp/msr101/s1; R0=/tmp/msr101/s0
run(){ tag=$1; shift; timeout 1700 $P "$@" > out/$tag.txt 2>&1; echo "$tag rc=$?" >> out/progress.txt; }
run f_ste1  hd $R1/hd f_ste1  --machine ste --mem 1024
run f_ste4  hd $R1/hd f_ste4  --machine ste --mem 4096
run f_mste  hd $R1/hd f_mste  --machine megaste --mem 1024 --tos 2.06
run f_st    hd $R1/hd f_st    --machine st --mem 1024 --tos 1.04
run f_fl    fl $R1/fl f_fl    --machine ste --mem 1024
run f_flB   fl $R1/fl f_flB   --machine ste --mem 1024 --driveb
for v in 1 0; do
 R=$R1; [ $v = 0 ] && R=$R0
 run p${v}_ste1 hd $R/hd p${v}_ste1 --machine ste --mem 1024 --pace-only
 run p${v}_ste4 hd $R/hd p${v}_ste4 --machine ste --mem 4096 --pace-only
 run p${v}_mste hd $R/hd p${v}_mste --machine megaste --mem 1024 --tos 2.06 --pace-only
 run p${v}_st   hd $R/hd p${v}_st   --machine st --mem 1024 --tos 1.04 --pace-only
 run p${v}_fl   fl $R/fl p${v}_fl   --machine ste --mem 1024 --pace-only
done
echo ALLDONE >> out/progress.txt
