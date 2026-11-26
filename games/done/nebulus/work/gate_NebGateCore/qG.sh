cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
O=/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebGateCore/out
while [ ! -f $O/qF.done ]; do sleep 5; done
echo "== mega ctl $(date +%T)"
python3 work/gate_NebGateCore/ikg.py ctl megaste > $O/ik_ctl_mega.txt 2>&1
echo done > $O/qG.done
