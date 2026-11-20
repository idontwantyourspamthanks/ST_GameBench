#!/usr/bin/env bash
# Run every PSG gate cell for one build: tools/hunt_psg_all.sh before|after   (one Hatari at a time; logs in work/psg/)
set -u
cd "$(dirname "$(readlink -f "$0")")/.."
W=$1; ONLY=${2:-.}
if [ "$W" = before ]; then FL=dist/Hunter_v1.2_patched_floppy_2026-11-13.zip; FL2=dist/Hunter_v1.2_patched_floppy_2disk_2026-11-13.zip; HD=dist/Hunter_v1.2_patched_hd_2026-11-13.zip
else FL=${PSG_FL:-build/psg_after_fl}; FL2=${PSG_FL2:-build/psg_after_fl2}; HD=${PSG_HD:-build/psg_after}; fi
mkdir -p work/psg
# a boot that fails is retried (up to 3 attempts: the title sometimes ignores the harness keys on a loaded host); every attempt keeps its log
run() { n=$1; shift; [[ "$n" =~ $ONLY ]] || return 0; for t in 1 2 3; do timeout 1500 python3 tools/hunt_psg.py "${W}_$n" "$@" > "work/psg/${W}_$n.try$t.log" 2>&1; cp "work/psg/${W}_$n.try$t.log" "work/psg/${W}_$n.log"; grep -q "boot=OK" "work/psg/${W}_$n.log" && break; done; echo "attempts=$t $(grep -h '^RESULT' work/psg/${W}_$n.log || echo "RESULT ${W}_$n: NO RESULT")"; }
run floppy_ste   --kind floppy  --src $FL  --machine ste --save
run floppy2_ste  --kind floppy2 --src $FL2 --machine ste --save
run hd_ste       --kind hd      --src $HD  --machine ste
run floppy_mste8  --kind floppy --src $FL  --machine megaste --mhz 8 --save
run floppy_mste16 --kind floppy --src $FL  --machine megaste --mhz 16 --save
run hd_mste8     --kind hd      --src $HD  --machine megaste --mhz 8
run hd_mste16    --kind hd      --src $HD  --machine megaste --mhz 16
run floppy_st    --kind floppy  --src $FL  --machine st
run hd_st        --kind hd      --src $HD  --machine st
run hd_tt        --kind hd      --src $HD  --machine tt
echo ALLDONE $W
