#!/bin/sh
# per-pass work (mt_* off): stock and cumulative mr_* sets, both scenes. usage: run_work.sh OUTLOG [passes]
cd "$(dirname "$0")/../.."
P=${2:-50}
for scene in race_start race_grid; do
  python3 work/render/work_live.py $scene --passes $P --out work/render/w_${scene}_stock.json
  python3 work/render/work_live.py $scene --only mr_edge --passes $P --out work/render/w_${scene}_edge.json
  python3 work/render/work_live.py $scene --only mr_edge mr_map --passes $P --out work/render/w_${scene}_edge_map.json
  python3 work/render/work_live.py $scene --only mr_edge mr_map mr_digit --passes $P --out work/render/w_${scene}_all3.json
  for v in edge edge_map all3; do python3 work/render/work_live.py --cmp work/render/w_${scene}_stock.json work/render/w_${scene}_$v.json; done
done
