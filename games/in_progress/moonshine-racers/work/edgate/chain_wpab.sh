#!/bin/bash
# WP-A/B gate chain (MSRLenAB). Sequential, one Hatari at a time.  envab.sh work/edgate/chain_wpab.sh [hd|fl|v1|quick|all]
cd "$(dirname "$(readlink -f "$0")")/../.."
HD=/tmp/msrwpab/hd FL=/tmp/msrwpab/fl HDO=/tmp/msrwpab/hd_old FLO=/tmp/msrwpab/fl_old
L2=work/trackedit/fixtures/len2.trk C3=work/camphd/camp/c3.trk TD=work/testdisk/MSTRACKS.TRK
run() { python3 work/edgate/len2.py "$@" 2>&1 | grep -E "^(== |PREDICT|CHECK|START|FINISH|DRIVE|TIMEOUT|RATE|BOOT)" ; }
case "$1" in
hd) for t in 0 1 2 3 4; do for m in info to drive; do [ $t = 3 -a $m = drive ] && continue; run --kind hd --build $HD --camp $L2 --track $t --mode $m; done; done ;;
fl) for t in 0 1 2 3 4; do for m in to drive; do [ $t = 3 -a $m = drive ] && continue; run --kind fl --build $FL --camp $L2 --track $t --mode $m; done; done ;;
v1) for t in 0 1 2; do for b in new old; do
      B=$HD; [ $b = old ] && B=$HDO
      for m in info to; do
        [ $m = to -a $t != 0 ] && continue
        run --kind hd --build $B --camp $C3 --track $t --mode $m --tag v1_hd_c3_t${t}_${m}_$b
        run --kind hd --build $B --camp $TD --track $t --mode $m --tag v1_hd_td_t${t}_${m}_$b
      done
    done; done ;;
v1fl) for t in 0 1 2; do for b in new old; do
      B=$FL; [ $b = old ] && B=$FLO
      for m in info to; do
        [ $m = to -a $t != 0 ] && continue
        run --kind fl --build $B --camp $C3 --track $t --mode $m --tag v1_fl_c3_t${t}_${m}_$b
      done
    done; done ;;
quick) for mc in megaste st; do run --kind hd --machine $mc --build $HD --camp $L2 --track 1 --mode info; done ;;
esac
