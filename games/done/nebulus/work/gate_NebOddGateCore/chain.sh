cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
N=/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
M=work/gate_NebOddGateCore; O=$M/out; HD=/tmp/oddcore/hd; OLD=/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebGateCore/unz/NEBULUS
step(){ echo "== $1 $(date +%T)"; }
step e98; python3 $M/e98_g.py > $O/e98.txt 2>&1
step cells_ste; python3 $M/cell_g.py $HD $M/cg_ste ste 1024 1.62 > $O/cg_ste.txt 2>&1
python3 $M/cell_g.py $HD $M/cg_st st 1024 1.04 > $O/cg_st.txt 2>&1
step dump; python3 $M/dumpcmp_g.py $OLD ste v11 > $O/dump_v11_ste.txt 2>&1; python3 $M/dumpcmp_g.py $HD ste v111 > $O/dump_v111_ste.txt 2>&1
step ik; python3 $M/ikg.py snap ste > $O/ik_snap_ste.txt 2>&1; python3 $M/ikg.py sweep ste > $O/ik_sweep_ste.txt 2>&1; python3 $M/ikg.py rand ste 8 7 > $O/ik_rand_ste.txt 2>&1
step lift; cd $M/lift; python3 mksnap2.py $HD /tmp/oddcore/lp/ste_ship ste 6 > $N/$O/lift_mksnap.txt 2>&1
for i in 1 2; do python3 ride2.py /tmp/oddcore/lp/ste_ship_t6.sav ship_t6_r$i 24 1 ste $HD > $N/$O/lift_ride_r$i.txt 2>&1; python3 ana.py /tmp/oddcore/lp/tr_ship_t6_r$i/log.txt > $N/$O/lift_ana_r$i.txt 2>&1; done
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
step shot; python3 $M/shot/mkledge_g.py > $O/shot_mkledge.txt 2>&1; python3 $M/shot/hat_g.py /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/$M/shot/ledge_ship.sav ship > $O/shot_ship.txt 2>&1
step junk_ste; python3 $M/jrg.py $HD ste rs v111 1 2 3 > $O/junk_ste_rs.jsonl 2> $O/junk_ste_rs.err; python3 $M/jrg.py $HD ste all v111 1 2 3 > $O/junk_ste_all.jsonl 2> $O/junk_ste_all.err
python3 $M/capture_g.py $HD ste ocste > $O/capture_ste.txt 2>&1; python3 $M/jrg.py $HD ste leftover:ocste v111 1 2 > $O/junk_ste_left.jsonl 2> $O/junk_ste_left.err
step train_ste; python3 $M/train_g.py ste > $O/train_ste.txt 2>&1
echo ste_done > $O/ste.done
step mega; python3 $M/cell_g.py $HD $M/cg_mega megaste 4096 2.06 > $O/cg_mega.txt 2>&1
python3 $M/train_g.py megaste > $O/train_mega.txt 2>&1
python3 $M/ikg.py snap megaste > $O/ik_snap_mega.txt 2>&1; python3 $M/ikg.py sweep megaste > $O/ik_sweep_mega.txt 2>&1
step junk_mega; python3 $M/jrg.py $HD megaste rs v111 1 2 > $O/junk_mega_rs.jsonl 2> $O/junk_mega_rs.err; python3 $M/jrg.py $HD megaste all v111 1 2 > $O/junk_mega_all.jsonl 2> $O/junk_mega_all.err
python3 $M/capture_g.py $HD megaste ocmega > $O/capture_mega.txt 2>&1; python3 $M/jrg.py $HD megaste leftover:ocmega v111 1 2 > $O/junk_mega_left.jsonl 2> $O/junk_mega_left.err
python3 $M/dumpcmp_g.py $HD megaste v111 > $O/dump_v111_mega.txt 2>&1; python3 $M/dumpcmp_g.py $OLD megaste v11 > $O/dump_v11_mega.txt 2>&1
echo all_done > $O/all.done
