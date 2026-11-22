#!/bin/bash
# env for the milestone 2b gates (MSREditor3): private HOME, local Hatari 2.6.1, own work dir /tmp/msred3, own logs (logs3/)
export HOME=/tmp/msred3_home
export HATARI=/home/ryan/Code/AtariST/hattari/build/src/hatari
export CG_TMP=/tmp/msred3/run
export ED_TMP=/tmp/msred3 ED_BUILD=/tmp/msred3/hd
export CG_LOGS="$(dirname "$(readlink -f "$0")")/logs3"
mkdir -p /tmp/msred3_home /tmp/msred3/run "$CG_LOGS"
exec "$@"
