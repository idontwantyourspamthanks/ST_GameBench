#!/bin/bash
# milestone 2c gate chain (tile-grid editor; one Hatari at a time): fresh HD + floppy builds, then every cell of RESULTS_m2c.md.  ./chain7.sh [cells...]  (default: all)
cd "$(dirname "$(readlink -f "$0")")/../.."
E=work/edgate/env8.sh; G=work/edgate; T=/tmp/msred8
python3 tools/msrpatch.py verify | tail -1
python3 tools/msrpatch.py build --out $T/hd | grep -E "MSEDIT|built"
python3 tools/msrpatch.py build --floppy --out $T/fl | grep -E "payload|built"
md5sum $T/hd/RUNME.TOS $T/hd/FILES/MSEDIT.OVL $T/fl/disk_a.st $T/fl/disk_b.st $T/v11fl/MOONSHR_floppy/disk_a.st $T/v11fl/MOONSHR_floppy/disk_b.st
want() { [ -z "$CELLS" ] || [[ " $CELLS " == *" $1 "* ]]; }
CELLS="$*"
want ed2    && $E python3 $G/ed2.py --kind stock --tag ed2_stock_ste2m
want speed  && $E python3 $G/speed.py --tag speed_ste2m
want td3    && $E python3 $G/td3.py --tag td3_ste2m
want shots  && $E python3 $G/shots.py
want qstr   && $E python3 $G/ed2.py --kind straight --quick --tag q_straight_ste2m
want qmste  && $E python3 $G/ed2.py --kind stock --quick --machine megaste --tag q_stock_mste2m
want qst    && $E python3 $G/ed2.py --kind stock --quick --machine st --tag q_stock_st2m
want tdmste && $E python3 $G/td3.py --quick --nonormal --machine megaste --tag td3_mste2m
want tdst   && $E python3 $G/td3.py --quick --nonormal --machine st --tag td3_st2m
want w2m    && $E python3 $G/welcome.py --tag w2m --full
want w1m    && $E python3 $G/welcome.py --tag w1m --mem 1024
want abs    && $E python3 $G/abs1m.py --machine ste
if want fl; then
  $E python3 $G/flshot.py --tag fl1m_new --mem 1024 --disk $T/fl/disk_a.st
  $E python3 $G/flshot.py --tag fl1m_v11 --mem 1024 --disk $T/v11fl/MOONSHR_floppy/disk_a.st
  for n in s70 s78; do cmp -n 32000 $T/fls_fl1m_new/$n.bin $T/fls_fl1m_v11/$n.bin && echo "FLOPPY 1 MB title screen $n: the 32000 visible bytes are IDENTICAL to the v1.1 floppy build's" || echo "FLOPPY 1 MB title screen $n: DIFFERENT"; done
  $E python3 $G/sitefl.py --mem 1024 --disk $T/fl/disk_a.st
  $E python3 $G/flhint.py --tag flhint_2m --mem 2048 --disk $T/fl/disk_a.st --f10
fi
echo CHAIN DONE
