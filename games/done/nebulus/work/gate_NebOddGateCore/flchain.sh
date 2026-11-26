cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebOddGateCore
O=out; GM=/tmp/oddcore/game.st; F=/tmp/oddcore/fo
cp /tmp/oddcore/fl/Nebulus_game_disk.st $GM; md5sum $GM > $O/fl_game_md5.txt
while [ ! -f $O/all.done ]; do sleep 10; done
step(){ echo "== $1 $(date +%T)"; }
step fgate_ste; python3 /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/floppy/fgate.py $GM /tmp/oddcore/fg_ste ste 1024 1.62 patched > $O/fg_ste.txt 2>&1
step fo_ste; python3 fo180.py $GM /tmp/oddcore/fo/w_ste ste $F/odd2.ovl $F/looks.ovl $F/stress05.ovl $F/stress01.ovl --quick > $O/fo_ste.txt 2>&1
step fge_ste; python3 fge.py $GM /tmp/oddcore/g_ste ste fuzzsubset > $O/fge_ste.txt 2>&1
step fge2_ste; python3 fge2.py $GM /tmp/oddcore/h2_ste ste > $O/fge2_ste.txt 2>&1
step f161_ste; python3 f161_nfe.py $GM /tmp/oddcore/h1_ste ste skipfuzz > $O/f161_ste.txt 2>&1
step fgate_st; python3 /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/floppy/fgate.py $GM /tmp/oddcore/fg_st st 1024 1.04 patched > $O/fg_st.txt 2>&1
step fo_st; python3 fo180.py $GM /tmp/oddcore/fo/w_st st $F/odd2.ovl $F/looks.ovl --quick > $O/fo_st.txt 2>&1
step fge_st; python3 fge.py $GM /tmp/oddcore/g_st st fuzzsubset > $O/fge_st.txt 2>&1
step fgate_mste; python3 /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/floppy/fgate.py $GM /tmp/oddcore/fg_mste megaste 4096 2.06 patched > $O/fg_mste.txt 2>&1
step fo_mste; python3 fo180.py $GM /tmp/oddcore/fo/w_mste megaste $F/odd2.ovl $F/looks.ovl --quick > $O/fo_mste.txt 2>&1
step fge_mste; python3 fge.py $GM /tmp/oddcore/g_mste megaste fuzzsubset > $O/fge_mste.txt 2>&1
step fge2_st; python3 fge2.py $GM /tmp/oddcore/h2_st st > $O/fge2_st.txt 2>&1
step fge2_mste; python3 fge2.py $GM /tmp/oddcore/h2_mste megaste > $O/fge2_mste.txt 2>&1
echo done > $O/fl.done
