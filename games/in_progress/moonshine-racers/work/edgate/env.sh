#!/bin/bash
# env for every Hatari run of the editor gates: private HOME, the local Hatari 2.6.1 build, own log dir
export HOME=/tmp/msred_home
export HATARI=/home/ryan/Code/AtariST/hattari/build/src/hatari
export CG_LOGS="$(dirname "$(readlink -f "$0")")/logs"
mkdir -p /tmp/msred_home /tmp/msrc3 /tmp/msred
exec "$@"
