#!/bin/bash
# env for the milestone 2b gates (MSREditor3): private HOME, local Hatari 2.6.1, own work dir /tmp/msred4, own logs (logs4/)
export HOME=/tmp/msred4_home
export HATARI=/home/ryan/Code/AtariST/hattari/build/src/hatari
export CG_TMP=/tmp/msred4/run
export ED_TMP=/tmp/msred4 ED_BUILD=/tmp/msred4/hd
export CG_LOGS="$(dirname "$(readlink -f "$0")")/logs4"
mkdir -p /tmp/msred4_home /tmp/msred4/run "$CG_LOGS"
exec "$@"
