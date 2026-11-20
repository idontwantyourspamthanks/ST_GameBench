#!/usr/bin/env bash
cd "$(dirname "$0")"
while pgrep -f "release_gates.sh" >/dev/null; do sleep 15; done
export MW2S_SOUND=50066 MW2S_EXTRA="--trace psg_write" MW2S_MEM=4096
python3 ymab.py ym_tt_ship2 tt 306 8 1 /tmp/mw2s/ship > out/ym_tt_ship2.log 2>&1
python3 ymdiff.py /tmp/mw2s/ym_tt_ship/fdc.trace /tmp/mw2s/ym_tt_ship2/fdc.trace > out/ymdiff_tt_ship_vs_ship2.txt 2>&1
echo "== v1.6 vs v1.6 (TT)"; cut -c1-200 out/ymdiff_tt_ship_vs_ship2.txt | head -12
echo "== ALL5 DONE"
