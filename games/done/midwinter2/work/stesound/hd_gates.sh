#!/usr/bin/env bash
# HD zip gates (shipped Midwinter2_v1.6.1_patched_<date>.zip unzipped to /tmp/mw2s/hd/MW2PATCH): asn_mus_cold.py run = cold boot of RUNME.TOS from C:, logo (Amiga tune from the logo), --intro soak,
# M/J/K, hall, map (--to map: the script's own boss-screen step fails identically on the shipped v1.6 HD zip), bank-in-RAM check vs build/asn_bank.bin.  Runs in a CLEAN environment (env -i).
# (asn_live.setup_home only READS the real hatari config to seed its private HOME /tmp/asn/home_<pid>)
R=/home/ryan/Code/AtariST/gamebench/games/done/midwinter2; cd $R
B=/tmp/mw2s/hd/MW2PATCH
run() { n=$1; shift; echo "== $n"; env -i PATH="$PATH" HOME="$HOME" HATARI=/home/ryan/Code/AtariST/hattari/build/src/hatari "$@" timeout 2400 python3 tools/asn_mus_cold.py run $n $MACH $TOSV $MEM hd $B --intro $INTRO --to $TO 2>&1 | grep -E "^\[(intro |mjk|hall |map)|bank checks|EXC|never|Traceback" | cut -c1-200; }
MACH=ste TOSV=162 MEM=1024 INTRO=120 TO=map run hd161_ste
MACH=megaste TOSV=206 MEM=1024 INTRO=120 TO=map run hd161_mste8
MACH=megaste TOSV=206 MEM=1024 INTRO=120 TO=map run hd161_mste16 MW2_CPUCLOCK=16
MACH=tt TOSV=306 MEM=4096 INTRO=60 TO=intro run hd161_tt
echo "== HD GATES DONE"
