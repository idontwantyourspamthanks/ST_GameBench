#!/bin/bash
# sequential debugger-driven calls of the scratch HAGA-window reader (one Hatari at a time)
cd "$(dirname "$0")/../.."
R="work/trackloader/run_hatari_env.sh python3 work/trackloader/call_trk.py"
S=work/trackloader/snap; D=work/trackloader/disk/campaign.st; O=work/trackloader
$R --snap $S/ste_4096.sav --machine ste --mem 4096 --path 'A:\MSTRACKS.TRK' > $O/call_ste4m_nofloppy.txt 2>&1
$R --snap $S/ste_4096.sav --machine ste --mem 4096 --path 'A:\MSTRACKS.TRK' --floppy $D --drive > $O/call_ste4m_floppy_driving.txt 2>&1
$R --snap $S/megaste_2048.sav --machine megaste --tos 2.06 --mem 2048 --path 'MSTRACKS.TRK' --hdfile --drive > $O/call_mste2m_hd_driving.txt 2>&1
$R --snap $S/megaste_2048.sav --machine megaste --tos 2.06 --mem 2048 --path 'A:\MSTRACKS.TRK' --floppy $D --drive > $O/call_mste2m_floppy_driving.txt 2>&1
$R --snap $S/megaste_4096.sav --machine megaste --tos 2.06 --mem 4096 --path 'A:\MSTRACKS.TRK' --floppy $D --calls 2 --drive > $O/call_mste4m_floppy_2calls.txt 2>&1
