#!/usr/bin/env bash
# usage: run.sh NAME ARGS...   -> work/retire/runs/NAME.txt
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/powermonger
n=$1; shift
python3 tools/pmretire.py "$@" > work/retire/runs/$n.txt 2>&1
echo "exit $?" >> work/retire/runs/$n.txt
