#!/bin/bash
# env for the milestone 2c gates (MSREditor6): private HOME, local Hatari 2.6.1, own work dir /tmp/msred6, own logs (logs6/)
export HOME=/tmp/msred6_home
export HATARI=/home/ryan/Code/AtariST/hattari/build/src/hatari
export CG_TMP=/tmp/msred6/run
export ED_TMP=/tmp/msred6 ED_BUILD=/tmp/msred6/hd
export CG_LOGS="$(dirname "$(readlink -f "$0")")/logs6"
mkdir -p /tmp/msred6_home /tmp/msred6/run "$CG_LOGS"
exec "$@"
