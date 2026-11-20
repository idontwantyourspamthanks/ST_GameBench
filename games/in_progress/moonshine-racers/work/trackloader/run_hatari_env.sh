#!/bin/bash
# env for every scratch Hatari run in this study: private HOME, the local Hatari 2.6.1 build
export HOME=/tmp/msrl_home
export HATARI=/home/ryan/Code/AtariST/hattari/build/src/hatari
exec "$@"
