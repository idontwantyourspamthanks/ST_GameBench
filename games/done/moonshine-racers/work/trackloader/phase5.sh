#!/bin/bash
cd "$(dirname "$0")/../.."
while pgrep -f work/trackloader/phase4.sh >/dev/null; do sleep 3; done
E=work/trackloader/run_hatari_env.sh; O=work/trackloader; S=$O/snap
$E python3 $O/hook_test.py --snap $S/ste_4096.sav --machine ste --mem 4096 > $O/hook_test_ste4m.txt 2>&1
$E python3 $O/hook_test.py --snap $S/megaste_2048.sav --machine megaste --tos 2.06 --mem 2048 > $O/hook_test_mste2m.txt 2>&1
