#!/bin/bash
cd "$(dirname "$0")/../.."
while pgrep -f "work/trackloader/phase[67].sh" >/dev/null; do sleep 3; done
E=work/trackloader/run_hatari_env.sh; O=work/trackloader
$E python3 $O/gate_probe.py --machine ste --mem 2048 > $O/gate_probe_ste2m.txt 2>&1
$E python3 $O/gate_probe.py --machine megaste --tos 2.06 --mem 2048 > $O/gate_probe_mste2m.txt 2>&1
