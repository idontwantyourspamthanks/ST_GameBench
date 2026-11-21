#!/usr/bin/env bash
# One cell of the matrix of work/notes/banktail.md per call (one Hatari at a time; chain calls from ONE tracked job, e.g.  for c in ms16 ms4 ...; do run_all.sh $c; done).
# Raw output: /tmp/mw2tail/<cell>.out, work/banktail/out/<cell>.txt.
# Needs the unzipped release zips in /tmp/mw2tail/rel/{hd,fl}: unzip dist/Midwinter2_v1.6.1_patched_2026-11-20.zip -d /tmp/mw2tail/rel/hd, ..._floppies_... -d /tmp/mw2tail/rel/fl
R=/home/ryan/Code/AtariST/gamebench/games/done/midwinter2; cd $R
HD=/tmp/mw2tail/rel/hd/MW2PATCH; FL=/tmp/mw2tail/rel/fl
run() { n=$1; shift; echo "== $n $*"; timeout 2400 python3 work/banktail/walk.py $n "$@" > /tmp/mw2tail/$n.out 2>&1; echo "exit $?"; }
case "$1" in
  ste1)    run ste1   ste     162 1024 hd $HD --to 3d --fx 2,17,19,24 ;;
  ms8)     run ms8    megaste 206 1024 hd $HD --to 3d --clk 8 --fx 2,17,19,24 ;;
  ms16)    run ms16   megaste 206 1024 hd $HD --to 3d --clk 16 --fx 2,17,19,24 ;;
  ms4)     run ms4    megaste 206 4096 hd $HD --to 3d --fx 2,17,19,24 ;;
  ste_tsr) python3 work/banktail/mktsr.py /tmp/mw2tail/tsr16/TSR16K.PRG 4000
           run ste_tsr ste 162 1024 hd $HD --to hall --auto /tmp/mw2tail/tsr16 ;;
  fl_ms)   run fl_ms  megaste 206 1024 floppy $FL --to 3d --fx 2,17,19,24 ;;
  fl_ste)  run fl_ste ste     162 1024 floppy $FL --to 3d --fx 2,17,19,24 ;;
  *) echo "usage: run_all.sh ste1|ms8|ms16|ms4|ste_tsr|fl_ms|fl_ste" ;;
esac
