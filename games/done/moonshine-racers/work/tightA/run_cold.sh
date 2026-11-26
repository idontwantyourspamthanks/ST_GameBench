#!/bin/sh
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
while ! grep -q DONE3 work/tightA/res/joy.log 2>/dev/null; do sleep 15; done
for m in 1024 4096; do python3 tools/msr_boot_test.py --machine ste --mem $m --game build/tighta --peek b2700 bef00 2>&1 | grep -E "RESULT|PEEK"; done > work/tightA/res/cold.log
python3 work/hud/build/play5_hd.py ste 1024 1.62 build/tighta 8 tA 16700 >> work/tightA/res/cold.log 2>&1
echo DONE4 >> work/tightA/res/cold.log
