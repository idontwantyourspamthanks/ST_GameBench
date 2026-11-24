#!/bin/bash
# env for the milestone 3 gates (MSREditor5): private HOME, local Hatari 2.6.1, own work dir /tmp/msred5, own logs (logs5/)
export HOME=/tmp/msred5_home
export HATARI=/home/ryan/Code/AtariST/hattari/build/src/hatari
export CG_TMP=/tmp/msred5/run
export ED_TMP=/tmp/msred5 ED_BUILD=/tmp/msred5/hd
export CG_LOGS="$(dirname "$(readlink -f "$0")")/logs5"
mkdir -p /tmp/msred5_home /tmp/msred5/run "$CG_LOGS"
exec "$@"
