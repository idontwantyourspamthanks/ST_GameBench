cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
O=/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebGateCore/out
while [ ! -f $O/qE.done ]; do sleep 5; done
python3 work/gate_NebGateCore/cell_g.py /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/dist/Nebulus_hd_v1.1.zip /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebGateCore/cg_ste ste 1024 1.62 > $O/cg_ste.txt 2>&1
python3 work/gate_NebGateCore/cell_g.py /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/dist/Nebulus_hd_v1.1.zip /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebGateCore/cg_st st 1024 1.04 > $O/cg_st.txt 2>&1
echo "== cg mega $(date +%T)"
python3 work/gate_NebGateCore/cell_g.py /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/dist/Nebulus_hd_v1.1.zip /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebGateCore/cg_mega megaste 4096 2.06 > $O/cg_mega.txt 2>&1
echo done > $O/qF.done
