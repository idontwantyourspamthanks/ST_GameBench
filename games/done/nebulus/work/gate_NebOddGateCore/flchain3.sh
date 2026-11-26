cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebOddGateCore
O=out; GM=/tmp/oddcore/game2.st
python3 f161_nfe.py $GM /tmp/oddcore/h1_st2 st skipfuzz > $O/f161_st.txt 2>&1
python3 f161_nfe.py $GM /tmp/oddcore/h1_mste2 megaste skipfuzz > $O/f161_mste.txt 2>&1
echo done > $O/fl3.done
