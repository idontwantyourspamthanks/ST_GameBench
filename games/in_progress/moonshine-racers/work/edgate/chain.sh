#!/bin/bash
# milestone 1 gate chain (one Hatari at a time): fresh HD build, STE 2 MB full, Mega STE 2 MB and ST 2 MB quick, map comparisons, STE 1 MB absence check
cd "$(dirname "$(readlink -f "$0")")/../.."
E=work/edgate/env.sh; S=work/edgate/logs/shots
python3 tools/msrpatch.py build --out /tmp/msred/hd | grep -E "wrote|built"
$E python3 work/edgate/eg.py --machine ste --mem 2048 --stock 0,7,14
$E python3 work/edgate/eg.py --machine megaste --mem 2048 --stock 7 --quick
$E python3 work/edgate/eg.py --machine st --mem 2048 --stock 7 --quick
for m in ste2m mste2m st2m; do
  python3 work/edgate/cmpmap.py $S/view_${m}_camp1.png work/camphd/camp/c3.trk --entry 0 -o $S/cmp_${m}_camp1.png
  for l in 0 7 14; do [ -f $S/view_${m}_stock$l.png ] && python3 work/edgate/cmpmap.py $S/view_${m}_stock$l.png $l -o $S/cmp_${m}_stock$l.png; done
done
echo "negative control (the screenshot of track 8 against the render of track 15 must MISMATCH):"
python3 work/edgate/cmpmap.py $S/view_ste2m_stock7.png 14
$E python3 work/edgate/abs1m.py --machine ste
python3 tools/msrpatch.py build --floppy --out /tmp/msred/fl | grep -E "payload"
md5sum /tmp/msred/fl/disk_a.st /tmp/msred/fl/disk_b.st /tmp/msred/v11f/MOONSHR_floppy/disk_a.st /tmp/msred/v11f/MOONSHR_floppy/disk_b.st
md5sum /tmp/msred/hd/RUNME.TOS /tmp/msred/hd/FILES/MSEDIT.OVL
