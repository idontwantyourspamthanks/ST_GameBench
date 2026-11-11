#!/bin/bash
# usage: run_type.sh tag snap groups ycnt xcnt mask [patchlist]
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/vehicles_water
python3 cmp.py "$@" 2>&1 | cut -c1-330 | tail -${TAILN:-30}
