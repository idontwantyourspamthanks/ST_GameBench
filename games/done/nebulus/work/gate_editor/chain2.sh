cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_editor/../editor
python3 e161.py /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_editor/hd/NEBULUS /tmp/ge_161ste2 ste skipfuzz > /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_editor/e161_ste_rerun.log 2>&1
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_editor/../junkram/gates
python3 e91_jr.py > /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_editor/e91.log 2>&1
touch /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_editor/chain2.done
