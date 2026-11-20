#!/usr/bin/env bash
cd "$(dirname "$0")"
while pgrep -f "[r]un_c3.sh" >/dev/null; do sleep 15; done
timeout 1500 python3 cell16.py sb_mste206_8_d1r megaste 206 1024 /tmp/mw2f/ship 8 1 --ext st > out/sb_mste206_8_d1r.log 2>&1
