#!/bin/bash
# env for the test-drive crash investigation (MSRDriveCrash): private HOME, own work dir /tmp/msrcrash
export HOME=/tmp/msrcrash_home
export HATARI=/home/ryan/Code/AtariST/hattari/build/src/hatari
export CG_TMP=/tmp/msrcrash/run
export ED_TMP=/tmp/msrcrash ED_BUILD=/tmp/msrcrash/hd
export CG_LOGS=/tmp/msrcrash/logs
mkdir -p /tmp/msrcrash_home /tmp/msrcrash/run "$CG_LOGS"
exec "$@"
