cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
O=work/gate_NebGateCore/out
SH=/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebGateCore/unz/NEBULUS
while [ ! -f $O/qB.done ]; do sleep 5; done
echo "== mega ik $(date +%T)"
python3 work/gate_NebGateCore/ikg.py snap megaste > $O/ik_snap_mega.txt 2>&1
python3 work/gate_NebGateCore/ikg.py sweep megaste > $O/ik_sweep_mega.txt 2>&1
echo "== mega junk $(date +%T)"
python3 work/gate_NebGateCore/jrg.py $SH megaste rs ship 1 2 3 4 > $O/junk_mega_rs.jsonl 2> $O/junk_mega_rs.err
python3 work/gate_NebGateCore/jrg.py $SH megaste all ship 1 2 3 4 > $O/junk_mega_all.jsonl 2> $O/junk_mega_all.err
python3 work/gate_NebGateCore/capture_g.py $SH megaste gcmega > $O/capture_mega.txt 2>&1
python3 work/gate_NebGateCore/jrg.py $SH megaste leftover:gcmega ship 1 2 3 4 > $O/junk_mega_left.jsonl 2> $O/junk_mega_left.err
echo "== mega cell $(date +%T)"
python3 work/release/final_cell.py /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/dist/Nebulus_hd_v1.1.zip /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebGateCore/cell_mega megaste 4096 2.06 > $O/cell_mega.txt 2>&1
echo done > $O/qC.done
