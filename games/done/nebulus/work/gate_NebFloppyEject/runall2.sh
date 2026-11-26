cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebFloppyEject
G=/tmp/nfe/game_new.st
for m in ste st megaste; do
python3 fge2.py $G /tmp/nfe/h2_$m $m > /tmp/nfe/out2_$m.txt 2>&1
python3 f161_nfe.py $G /tmp/nfe/h1_$m $m > /tmp/nfe/out1_$m.txt 2>&1
done
echo done > /tmp/nfe/out2_done
