cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebFloppyEject
G=/tmp/nfe/game_new.st
python3 fge.py $G /tmp/nfe/g_ste ste fuzzsubset > /tmp/nfe/out_ste.txt 2>&1
python3 fge.py $G /tmp/nfe/g_st st fuzzsubset > /tmp/nfe/out_st.txt 2>&1
python3 fge.py $G /tmp/nfe/g_mste megaste fuzzsubset > /tmp/nfe/out_mste.txt 2>&1
python3 f161_nfe.py $G /tmp/nfe/g_f161 ste skipfuzz > /tmp/nfe/out_f161.txt 2>&1
echo done > /tmp/nfe/out_done
