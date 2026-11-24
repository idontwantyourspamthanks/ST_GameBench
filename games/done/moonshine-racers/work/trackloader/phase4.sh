#!/bin/bash
cd "$(dirname "$0")/../.."
E=work/trackloader/run_hatari_env.sh; O=work/trackloader; S=$O/snap
$E python3 $O/finish_test.py --snap $S/ste_4096.sav --machine ste --mem 4096 --secs 90 --tag finA > $O/finish_A.txt 2>&1
$E python3 $O/finish_test.py --snap $S/ste_4096.sav --machine ste --mem 4096 --secs 130 --poke-102c 14 --tag finB > $O/finish_B_campaign_end.txt 2>&1
$E python3 $O/hook_test.py --snap $S/ste_4096.sav --machine ste --mem 4096 > $O/hook_test_ste4m.txt 2>&1
$E python3 $O/boot_stale.py /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/hd 4096 > $O/boot_stale_hd_4m.txt 2>&1
$E python3 $O/boot_snap.py --game /tmp/msrl_dist/MOONSHR --machine ste --mem 2048 --tos 1.62 --out $S/ste_2048 --dump > $O/boot_ste_2048.txt 2>&1
