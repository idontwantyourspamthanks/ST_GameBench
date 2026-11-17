#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/mxfast
for n in restore_slots prerestore_short ring_window static_1308 kernel_long save_slots_short; do python3 cmpmx.py L10 left 60 2 X M neg=$n 2>&1 | grep -v "^  extras\|^  runs" | cut -c1-260; done > res/neg_M.txt
for n in g_restore_fields g_no_reset g_scan_short ring_window static_1308 kernel_long; do python3 cmpmx.py L10 left 60 2 X G neg=$n 2>&1 | grep -v "^  extras\|^  runs" | cut -c1-260; done > res/neg_G.txt
echo DONE > res/neg.done
