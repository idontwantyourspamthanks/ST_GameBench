#!/bin/bash
# env for the milestone 2c gates (MSREditor8): private HOME, local Hatari 2.6.1, own work dir /tmp/msred8, own logs (logs8/)
export HOME=/tmp/msred8_home
export HATARI=/home/ryan/Code/AtariST/hattari/build/src/hatari
export CG_TMP=/tmp/msred8/run
export ED_TMP=/tmp/msred8 ED_BUILD=/tmp/msred8/hd
export CG_LOGS="$(dirname "$(readlink -f "$0")")/logs8"
mkdir -p /tmp/msred8_home /tmp/msred8/run "$CG_LOGS"
exec "$@"
