cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_editor/../editor
python3 e161.py /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_editor/hd/NEBULUS /tmp/ge_161ste3 ste skipfuzz > /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_editor/e161_ste_rerun2.log 2>&1
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_editor
python3 g67.py /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_editor/hd/NEBULUS shots /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_editor/shots > g67_shots.log 2>&1
python3 g67.py /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_editor/hd/NEBULUS orig /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_editor/shots > g67_orig.log 2>&1
python3 g67.py /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_editor/hd/NEBULUS plain /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_editor/shots > g67_plain.log 2>&1
touch /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_editor/chain3.done
