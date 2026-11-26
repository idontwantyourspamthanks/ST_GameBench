#!/bin/bash
N=/tmp/ng12hd/nb; X=/tmp/ng12hd/x; M=work/core; O=$N/$M/out; HD=$X/oddcore/hd; OLD=$X/oddcore/hd111; L=/tmp/ng12hd/logs/core
mkdir -p $L; cd $N; export HOME=/tmp/ng12hd/home PYTHONUNBUFFERED=1
step(){ echo "== $1 $(date +%T)" >> $L/steps.txt; }
step e98; python3 $M/e98_g.py > $L/e98.txt 2>&1
step cell_ste; python3 $M/cell_g.py $HD $N/$M/cg_ste ste 1024 1.62 > $L/cg_ste.txt 2>&1
step cell_st; python3 $M/cell_g.py $HD $N/$M/cg_st st 1024 1.04 > $L/cg_st.txt 2>&1
step cell_mega; python3 $M/cell_g.py $HD $N/$M/cg_mega megaste 4096 2.06 > $L/cg_mega.txt 2>&1
step dump; python3 $M/dumpcmp_g.py $OLD ste v111 > $L/dump_v111_ste.txt 2>&1; python3 $M/dumpcmp_g.py $HD ste v12 > $L/dump_v12_ste.txt 2>&1
python3 $M/dumpcmp_g.py $OLD megaste v111 > $L/dump_v111_mega.txt 2>&1; python3 $M/dumpcmp_g.py $HD megaste v12 > $L/dump_v12_mega.txt 2>&1
step ik; python3 $M/ikg.py snap ste > $L/ik_snap_ste.txt 2>&1; python3 $M/ikg.py sweep ste > $L/ik_sweep_ste.txt 2>&1; python3 $M/ikg.py rand ste 8 7 > $L/ik_rand_ste.txt 2>&1
python3 $M/ikg.py snap megaste > $L/ik_snap_mega.txt 2>&1; python3 $M/ikg.py sweep megaste > $L/ik_sweep_mega.txt 2>&1
step lift; cd $N/$M/lift; python3 mksnap2.py $HD $X/oddcore/lp/ste_ship ste 6 > $L/lift_mksnap.txt 2>&1
for i in 1 2; do python3 ride2.py $X/oddcore/lp/ste_ship_t6.sav ship_t6_r$i 24 1 ste $HD > $L/lift_ride_r$i.txt 2>&1; python3 ana.py $X/oddcore/lp/tr_ship_t6_r$i/log.txt > $L/lift_ana_r$i.txt 2>&1; done
cd $N
step shot; python3 $M/shot/mkledge_g.py > $L/shot_mkledge.txt 2>&1; python3 $M/shot/hat_g.py $N/$M/shot/ledge_ship.sav ship > $L/shot_ship.txt 2>&1
step junk_ste; python3 $M/jrg.py $HD ste rs v12 1 2 3 > $L/junk_ste_rs.jsonl 2> $L/junk_ste_rs.err; python3 $M/jrg.py $HD ste all v12 1 2 3 > $L/junk_ste_all.jsonl 2> $L/junk_ste_all.err
python3 $M/capture_g.py $HD ste ocste > $L/capture_ste.txt 2>&1; python3 $M/jrg.py $HD ste leftover:ocste v12 1 2 > $L/junk_ste_left.jsonl 2> $L/junk_ste_left.err
step train_ste; python3 $M/train_g.py ste > $L/train_ste.txt 2>&1
step junk_mega; python3 $M/jrg.py $HD megaste rs v12 1 2 3 > $L/junk_mega_rs.jsonl 2> $L/junk_mega_rs.err; python3 $M/jrg.py $HD megaste all v12 1 2 3 > $L/junk_mega_all.jsonl 2> $L/junk_mega_all.err
python3 $M/capture_g.py $HD megaste ocmega > $L/capture_mega.txt 2>&1; python3 $M/jrg.py $HD megaste leftover:ocmega v12 1 2 > $L/junk_mega_left.jsonl 2> $L/junk_mega_left.err
step train_mega; python3 $M/train_g.py megaste > $L/train_mega.txt 2>&1
echo done > $L/done
