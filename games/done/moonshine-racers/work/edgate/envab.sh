#!/bin/bash
# env for the WP-A/B gates (MSRLenAB): private HOME, local Hatari 2.6.1, own work dir /tmp/msrwpab, own logs (logs_wpab/)
export HOME=/tmp/msrwpab_home
export HATARI=/home/ryan/Code/AtariST/hattari/build/src/hatari
export CG_TMP=/tmp/msrwpab/run
export CG_LOGS="$(dirname "$(readlink -f "$0")")/logs_wpab"
mkdir -p /tmp/msrwpab_home /tmp/msrwpab/run "$CG_LOGS"
exec "$@"
