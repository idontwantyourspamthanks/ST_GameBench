#!/bin/bash
# env for the milestone 2c gates (MSREditor7): private HOME, local Hatari 2.6.1, own work dir /tmp/msred7, own logs (logs7/)
export HOME=/tmp/msred7_home
export HATARI=/home/ryan/Code/AtariST/hattari/build/src/hatari
export CG_TMP=/tmp/msred7/run
export ED_TMP=/tmp/msred7 ED_BUILD=/tmp/msred7/hd
export CG_LOGS="$(dirname "$(readlink -f "$0")")/logs7"
mkdir -p /tmp/msred7_home /tmp/msred7/run "$CG_LOGS"
exec "$@"
