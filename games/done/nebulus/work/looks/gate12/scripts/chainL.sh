#!/bin/bash
N=/tmp/ng12hd/nb; X=/tmp/ng12hd/x; B=$X/b; R=$X/r; L=/tmp/ng12hd/logs/looks; W=/tmp/ng12hd/wd; mkdir -p $L $W
cd $N; export HOME=/tmp/ng12hd/home PYTHONUNBUFFERED=1
step(){ echo "== $1 $(date +%T)" >> $L/steps.txt; }
rl(){ python3 work/looks/run_look.py "$@"; }
step all12; rl $B/hd_all12 $R/all12_ste 12 camp ste > $L/all12_ste.log 2>&1; python3 work/looks/check_all12.py $R/base8_ste $R/all12_ste > $L/check_all12_ste.txt 2>&1
step eyes5; NOE=1 DELAY=2 rl $B/hd_eyes5 $R/eyes5_ste 5 camp ste > $L/eyes5_ste.log 2>&1
step eye3; NOE=1 DELAY=2 rl $B/hd_eye3 $R/eye3_ste 1 camp ste > $L/eye3_ste.log 2>&1
step eye4; NOE=1 DELAY=2 rl $B/hd_eye4 $R/eye4_ste 1 camp ste > $L/eye4_ste.log 2>&1
step negctl; rl $B/old_looks15 $R/neg_looks15_ste 15 camp ste > $L/neg_looks15_ste.log 2>&1; python3 work/looks/check_look.py $R/base8_ste $R/neg_looks15_ste looks15 > $L/neg_check_ste.txt 2>&1
step e202; REFDIR=$R/base8_megaste python3 work/editor/e202.py $X/user.img $W/e202_mega > $L/e202_mega.log 2>&1
echo done > $L/done
