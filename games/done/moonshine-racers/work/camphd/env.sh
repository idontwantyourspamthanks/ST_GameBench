#!/bin/bash
# env for every scratch Hatari run of the HD campaign work: private HOME, the local Hatari 2.6.1 build
export HOME=/tmp/camphd_home
mkdir -p $HOME/.config/hatari
export HATARI=/home/ryan/Code/AtariST/hattari/build/src/hatari
exec "$@"
