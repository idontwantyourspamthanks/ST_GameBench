#!/bin/bash
cd "$(dirname "$0")/../.."
echo "=== A: rd set, flips 10 40, state 120 (4 snapshots)"; python3 tools/msrabtest.py --only rd_geom rd_draw rd_init --flips 10 40 --state 120 2>&1 | tail -14
echo "=== B: tick ON (mt_sync), state 230, race_start race_drive"; python3 tools/msrabtest.py --only mr_edge mr_map mr_digit rd_geom rd_draw rd_init mt_clock mt_sync mt_pre --snapshots race_start race_drive --flips 10 --state 230 2>&1 | tail -8
echo "=== C: negative control"; python3 tools/msrabtest.py --only rd_geom rd_draw mr_negctl --snapshots race_start --flips 10 --state 0 2>&1 | tail -5
