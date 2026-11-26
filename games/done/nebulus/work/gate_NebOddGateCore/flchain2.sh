cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebOddGateCore
O=out; F=/tmp/oddcore/fo
cp /tmp/oddcore/fl/Nebulus_game_disk.st /tmp/oddcore/game2.st; GM=/tmp/oddcore/game2.st
step(){ echo "== $1 $(date +%T)"; }
step fgate_mste; python3 /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/floppy/fgate.py $GM /tmp/oddcore/fg_mste2 megaste 4096 2.06 patched > $O/fg_mste.txt 2>&1
step fo_mste; python3 fo180.py $GM /tmp/oddcore/fo/w_mste2 megaste $F/odd2.ovl $F/looks.ovl --quick > $O/fo_mste.txt 2>&1
step fge_mste; python3 fge.py $GM /tmp/oddcore/g_mste2 megaste fuzzsubset > $O/fge_mste.txt 2>&1
step fge2_mste; python3 fge2.py $GM /tmp/oddcore/h2_mste2 megaste > $O/fge2_mste.txt 2>&1
step fge_st; python3 fge.py $GM /tmp/oddcore/g_st2 st fuzzsubset > $O/fge_st.txt 2>&1
step fge2_st; python3 fge2.py $GM /tmp/oddcore/h2_st2 st > $O/fge2_st.txt 2>&1
echo done > $O/fl2.done
