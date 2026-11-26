cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
O=work/gate_NebGateCore/out
SH=/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebGateCore/unz/NEBULUS
while [ ! -f $O/qA2.done ]; do sleep 5; done
echo "== junk ste $(date +%T)"
python3 work/gate_NebGateCore/jrg.py $SH ste rs ship 1 2 3 4 5 > $O/junk_ste_rs.jsonl 2> $O/junk_ste_rs.err
python3 work/gate_NebGateCore/jrg.py $SH ste all ship 1 2 3 4 5 > $O/junk_ste_all.jsonl 2> $O/junk_ste_all.err
python3 work/gate_NebGateCore/capture_g.py $SH ste gcste > $O/capture_ste.txt 2>&1
python3 work/gate_NebGateCore/jrg.py $SH ste leftover:gcste ship 1 2 3 4 > $O/junk_ste_left.jsonl 2> $O/junk_ste_left.err
echo "== cells $(date +%T)"
python3 work/release/final_cell.py /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/dist/Nebulus_hd_v1.1.zip /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebGateCore/cell_ste ste 1024 1.62 > $O/cell_ste.txt 2>&1
python3 work/release/final_cell.py /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/dist/Nebulus_hd_v1.1.zip /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebGateCore/cell_st st 1024 1.04 > $O/cell_st.txt 2>&1
echo "== noise dump $(date +%T)"
python3 work/gate_NebGateCore/dumpcmp_g.py $SH ste shipped2 > $O/dumpcmp2.txt 2>&1
echo done > $O/qB.done
