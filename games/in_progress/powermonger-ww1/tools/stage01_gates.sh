#!/bin/bash
# Stage-1 gate chain (one Hatari at a time, private HOME inside each work dir).  Logs: work/runs/<name>.txt
# Needs disks/ea.st and (for the disk swap the game itself asks for) the user's original Powermonger floppy, see tools/pmww.py PM_DISK.
set -u
cd "$(dirname "$0")/.."
W=${WORK:-/tmp/pmww1s1}
python3 tools/wwpatch.py build --none --floppy --out build/core_only >/dev/null
python3 tools/wwpatch.py build --floppy --out build/default >/dev/null
python3 tools/wwpatch.py build --floppy --fill --out build/fill >/dev/null
python3 tools/wwpatch.py build --floppy --corrupt --out build/corrupt >/dev/null
mkdir -p work/runs
run() {  # name, args...
  local n=$1; shift; rm -rf "$W/$n"
  python3 tools/wwgate.py "$@" --workdir "$W/$n" > "work/runs/$n.txt" 2>&1
}
run handover_core_only handover --disk build/core_only/floppy.st --tag core_only
run default_ste   cell --disk build/default/floppy.st --manifest build/default/manifest.json --tag default
run fill_ste      cell --disk build/fill/floppy.st    --manifest build/fill/manifest.json    --tag fill
run corrupt_ste   cell --disk build/corrupt/floppy.st --manifest build/corrupt/manifest.json --tag corrupt --corrupt --steps boot,map
run core_only_ste cell --disk build/core_only/floppy.st --manifest build/core_only/manifest.json --tag core_only --steps boot,map,lose
run original_ste  cell --disk disks/ea.st --tag original
run default_megaste cell --disk build/default/floppy.st --manifest build/default/manifest.json --tag default --machine megaste --tos 2.06 --mem 4096 --steps boot,map,lose,win
run fill_megaste    cell --disk build/fill/floppy.st --manifest build/fill/manifest.json --tag fill --machine megaste --tos 2.06 --mem 4096 --steps boot,map,lose,win
