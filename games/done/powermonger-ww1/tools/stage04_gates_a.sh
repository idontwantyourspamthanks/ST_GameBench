#!/bin/bash
# Stage 4, items 1-3 (RAM guard, cache cap, HIGH-area fill gates).  One Hatari at a time, private HOME inside each work dir.  Logs: work/runs/s4_<name>.txt
set -u
cd "$(dirname "$0")/.."
W=${WORK:-/tmp/pmww1s4}
mkdir -p work/runs
FULL=boot,map,saveload,lose,win,continue,lose2,round3,win2,random
run() { local n=$1; shift; rm -rf "$W/$n"; python3 tools/wwgate.py cell "$@" --workdir "$W/$n" > "work/runs/s4_$n.txt" 2>&1; }
python3 tools/wwpatch.py build --floppy --out build/default >/dev/null
ALL=$(python3 tools/wwpatch.py list | awk '{print $1}')
python3 tools/wwpatch.py build --floppy --only $(echo "$ALL" | grep -v pm_cachecap) --out build/nocap >/dev/null
rm -rf "$W/patches_hineg"; cp -r patches "$W/patches_hineg"
sed -i 's/^\.ret:   rts/.ret:   move.b  #$7f,$ee500.l           ; TEST ONLY (negative control): a stray write into the HIGH reserve\n        rts/' "$W/patches_hineg/pm_cachecap.s"
WW_PATCHDIR="$W/patches_hineg" python3 tools/wwpatch.py build --floppy --out build/hineg >/dev/null
D="--disk build/default/floppy.st --manifest build/default/manifest.json --tag default --fill-hi --trace"
# M1 + M3a: the whole scenario, three machines
run ste_full     $D --steps $FULL --events-out "$W/ev_default.json"
run nocap_full   --disk build/nocap/floppy.st --manifest build/nocap/manifest.json --tag nocap --fill-hi --trace --steps $FULL --events-out "$W/ev_nocap.json"
python3 tools/wwgate.py cmpevents "$W/ev_default.json" "$W/ev_nocap.json" --tag M3a > work/runs/s4_m3a_compare.txt 2>&1
run megaste_full $D --steps $FULL --machine megaste --tos 2.06 --mem 4096
run st_full      $D --steps $FULL --machine st --tos 1.04 --mem 1024
# M3b: forced skip (cursor raised by $10000: LOSE and WIN end above the limit); M3c: the same without the cap must FAIL
run m3b_forced   $D --steps boot,map,lose,win --raise-cursor 10000
run m3c_nocap    --disk build/nocap/floppy.st --manifest build/nocap/manifest.json --tag nocap --fill-hi --trace --steps boot,map,lose --raise-cursor 10000 --expect-overrun
# M1 negative control: a stray write into the reserve
run m1_negative  --disk build/hineg/floppy.st --manifest build/hineg/manifest.json --tag hineg --fill-hi --trace --steps boot,map,lose
