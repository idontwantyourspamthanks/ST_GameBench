cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
for m in ste megaste; do
 python3 work/gate_NebGateCore/dumpcmp_g.py /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebGateCore/unz/NEBULUS $m shipped
 python3 work/gate_NebGateCore/dumpcmp_g.py /tmp/nebgc_fresh $m fresh
done
echo done > work/gate_NebGateCore/out/q_dump.done
