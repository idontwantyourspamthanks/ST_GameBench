#!/bin/bash
# Stage-3 gate chain (one Hatari at a time, private HOME inside each work dir).  Logs: work/runs/s3_<name>.txt
# 1. the tooltip gate (tools/wwtt.py) on cold boots of the built floppies: STE full, no-key-labels build, Mega STE 4 MB and ST 1 MB (reduced),
# 2. the stage-2 matrix again with the tooltips in (tools/wwgate.py cells + tools/wwkeys.py).
set -u
cd "$(dirname "$0")/.."
W=${WORK:-/tmp/pmww1s3}
python3 tools/wwtt.py check > work/runs/s3_wording_check.txt 2>&1
python3 tools/wwpatch.py build --floppy --out build/default >/dev/null
python3 tools/wwpatch.py build --floppy --fill --out build/fill >/dev/null
python3 tools/wwpatch.py build --floppy --corrupt --out build/corrupt >/dev/null
python3 tools/wwpatch.py build --floppy --only pm_tooltip pm_noprot pm_noprot_box pm_nokeydisk pm_credit --out build/tt_nokeys >/dev/null
mkdir -p work/runs
tt() {  # name, args...
  local n=$1; shift; rm -rf "$W/$n"
  python3 tools/wwtt.py gate "$@" --workdir "$W/$n" --tag "$n" > "work/runs/s3_$n.txt" 2>&1
}
run() {
  local n=$1; shift; rm -rf "$W/$n"
  python3 tools/wwgate.py "$@" --workdir "$W/$n" > "work/runs/s3_$n.txt" 2>&1
}
tt tt_ste        --disk build/default/floppy.st --manifest build/default/manifest.json
tt tt_nokeys_ste --disk build/tt_nokeys/floppy.st --manifest build/tt_nokeys/manifest.json --quick
tt tt_megaste    --disk build/default/floppy.st --manifest build/default/manifest.json --machine megaste --tos 2.06 --mem 4096 --quick
tt tt_st         --disk build/default/floppy.st --manifest build/default/manifest.json --machine st --tos 1.04 --mem 1024 --quick
STEPS=boot,map,rate,soak,saveload,lose,win,round3
run default_ste     cell --disk build/default/floppy.st --manifest build/default/manifest.json --tag default --steps $STEPS
run fill_ste        cell --disk build/fill/floppy.st    --manifest build/fill/manifest.json    --tag fill    --steps $STEPS
run corrupt_ste     cell --disk build/corrupt/floppy.st --manifest build/corrupt/manifest.json --tag corrupt --corrupt --steps boot,map
run default_megaste cell --disk build/default/floppy.st --manifest build/default/manifest.json --tag default --machine megaste --tos 2.06 --mem 4096 --steps $STEPS
run default_st      cell --disk build/default/floppy.st --manifest build/default/manifest.json --tag default --machine st --tos 1.04 --mem 1024 --steps boot,map,lose
python3 tools/wwkeys.py --disk build/default/floppy.st --manifest build/default/manifest.json --workdir "$W/keys" --tag keys > work/runs/s3_keys_ste.txt 2>&1
