#!/usr/bin/env bash
# usage: runq.sh NAME CMD...   (cmd = tool + args, run from the game dir) -> work/release/runs/NAME.txt
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/powermonger
n=$1; shift
python3 "$@" > work/release/runs/$n.txt 2>&1
echo "exit $?" >> work/release/runs/$n.txt
