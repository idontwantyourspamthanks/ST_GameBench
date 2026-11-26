#!/bin/bash
# cycles per pass, stock vs rd_*: run_work.sh TAG patchlist... ; scenes in $SCENES
cd "$(dirname "$0")/../.."
tag=$1; shift
for s in ${SCENES:-race_start race_grid}; do
  [ -f work/road/work/w_${s}_stock.json ] || python3 work/render/work_live.py $s --passes 45 --out work/road/work/w_${s}_stock.json | tee -a work/road/logs/work_$tag.txt
  python3 work/render/work_live.py $s --only "$@" --passes 45 --out work/road/work/w_${s}_$tag.json | tee -a work/road/logs/work_$tag.txt
  python3 work/render/work_live.py --cmp work/road/work/w_${s}_stock.json work/road/work/w_${s}_$tag.json | tee -a work/road/logs/work_$tag.txt
done
