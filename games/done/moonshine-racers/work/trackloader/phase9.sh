#!/bin/bash
cd "$(dirname "$0")/../.."
while pgrep -f "work/trackloader/phase[78].sh" >/dev/null; do sleep 3; done
E=work/trackloader/run_hatari_env.sh; O=work/trackloader; S=$O/snap
cp $O/hook_test_ste4m.txt $O/hook_test_ste4m_run2.txt
$E python3 $O/hook_test.py --snap $S/ste_4096.sav --machine ste --mem 4096 > $O/hook_test_ste4m.txt 2>&1
