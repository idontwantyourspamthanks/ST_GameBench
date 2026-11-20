#!/bin/bash
# sequential cold boots of the shipped HD build (unzipped dist) -> race, dump RAM + memstate. One Hatari at a time.
cd "$(dirname "$0")/../.."
G=${G:-/tmp/msrl_dist/MOONSHR}
for cfg in "megaste 4096 2.06" "megaste 2048 2.06" "ste 4096 1.62"; do
  set -- $cfg
  work/trackloader/run_hatari_env.sh python3 work/trackloader/boot_snap.py --game $G --machine $1 --mem $2 --tos $3 --out work/trackloader/snap/$1_$2 --dump > work/trackloader/boot_$1_$2.txt 2>&1
done
