cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor
for m in ste megaste st; do python3 e150.py /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor/../gate_editor/hd/NEBULUS /tmp/ge_150$m $m > /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor/../gate_editor/e150_$m.log 2>&1; done
for m in ste megaste st; do python3 e140.py /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor/../gate_editor/hd/NEBULUS /tmp/ge_140$m $m > /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor/../gate_editor/e140_$m.log 2>&1; done
for m in ste megaste; do python3 e161.py /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor/../gate_editor/hd/NEBULUS /tmp/ge_161$m $m > /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor/../gate_editor/e161_$m.log 2>&1; done
touch /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor/../gate_editor/chain.done
