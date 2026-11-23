#!/bin/bash
# Stage-2 gate chain (one Hatari at a time, private HOME inside each work dir).  Logs: work/runs/s2_<name>.txt
# Needs disks/ea.st and games/done/powermonger/disks/protected.st (only for the builds without pm_nokeydisk: core-only, original).
set -u
cd "$(dirname "$0")/.."
W=${WORK:-/tmp/pmww1s2}
python3 tools/wwpatch.py build --none --floppy --out build/core_only >/dev/null
python3 tools/wwpatch.py build --floppy --out build/default >/dev/null
python3 tools/wwpatch.py build --floppy --fill --out build/fill >/dev/null
python3 tools/wwpatch.py build --floppy --corrupt --out build/corrupt >/dev/null
mkdir -p work/runs
run() {  # name, args...
  local n=$1; shift; rm -rf "$W/$n"
  python3 tools/wwgate.py "$@" --workdir "$W/$n" > "work/runs/s2_$n.txt" 2>&1
}
STEPS=boot,map,rate,soak,saveload,lose,win,round3
run default_ste     cell --disk build/default/floppy.st --manifest build/default/manifest.json --tag default --steps $STEPS
run fill_ste        cell --disk build/fill/floppy.st    --manifest build/fill/manifest.json    --tag fill    --steps $STEPS
run corrupt_ste     cell --disk build/corrupt/floppy.st --manifest build/corrupt/manifest.json --tag corrupt --corrupt --steps boot,map
run core_only_ste   cell --disk build/core_only/floppy.st --manifest build/core_only/manifest.json --tag core_only --steps boot,map,lose
run original_ste    cell --disk disks/ea.st --tag original
run default_megaste cell --disk build/default/floppy.st --manifest build/default/manifest.json --tag default --machine megaste --tos 2.06 --mem 4096 --steps $STEPS
run fill_megaste    cell --disk build/fill/floppy.st --manifest build/fill/manifest.json --tag fill --machine megaste --tos 2.06 --mem 4096 --steps $STEPS
run rate16_megaste  cell --disk build/default/floppy.st --manifest build/default/manifest.json --tag default16 --machine megaste --tos 2.06 --mem 4096 --mhz 16 --steps boot,map,rate
run default_st      cell --disk build/default/floppy.st --manifest build/default/manifest.json --tag default --machine st --tos 1.04 --mem 1024 --steps boot,map,lose
python3 tools/wwkeys.py --disk build/default/floppy.st --manifest build/default/manifest.json --workdir "$W/keys" --tag keys > work/runs/s2_keys_ste.txt 2>&1
