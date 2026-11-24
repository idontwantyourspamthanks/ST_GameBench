#!/bin/bash
# env for the milestone 2 editing gates: private HOME, the local Hatari 2.6.1 build, own log dir (logs2/)
export HOME=/tmp/msred2_home
export HATARI=/home/ryan/Code/AtariST/hattari/build/src/hatari
export CG_LOGS="$(dirname "$(readlink -f "$0")")/logs2"
mkdir -p /tmp/msred2_home /tmp/msred2 "$CG_LOGS"
exec "$@"
