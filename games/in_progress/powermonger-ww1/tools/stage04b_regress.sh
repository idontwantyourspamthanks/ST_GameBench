#!/bin/bash
# Stage 4b regression for ONE build on top of the committed default set: STE 1 MB cell (fill-hi + loader trace, boot..round3), keys, tooltip quick.
# usage: tools/stage04b_regress.sh NAME BUILD_DIR [extra wwgate cell args...]     Logs: work/runs/s4b_<NAME>_{ste,keys,tt}.txt, work dirs /tmp/pmww1s4b/<NAME>_*
set -u
cd "$(dirname "$0")/.."
N=$1; B=$2; shift 2
PFX=${PFX:-s4b}
W=${WORK:-/tmp/pmww1s4b}
rm -rf "$W/${N}_ste" "$W/${N}_keys" "$W/${N}_tt"
python3 tools/wwgate.py cell --disk $B/floppy.st --manifest $B/manifest.json --tag $N --fill-hi --trace --steps boot,map,rate,saveload,lose,win,round3 --workdir "$W/${N}_ste" "$@" > work/runs/${PFX:-s4b}_${N}_ste.txt 2>&1
python3 tools/wwkeys.py --disk $B/floppy.st --manifest $B/manifest.json --workdir "$W/${N}_keys" --tag ${N}_keys > work/runs/${PFX:-s4b}_${N}_keys.txt 2>&1
python3 tools/wwtt.py gate --disk $B/floppy.st --manifest $B/manifest.json --quick --workdir "$W/${N}_tt" --tag ${N}_tt > work/runs/${PFX:-s4b}_${N}_tt.txt 2>&1
grep -h "CELL DONE\|CELL FAILED\|FAIL" work/runs/${PFX:-s4b}_${N}_{ste,keys,tt}.txt | head -30
