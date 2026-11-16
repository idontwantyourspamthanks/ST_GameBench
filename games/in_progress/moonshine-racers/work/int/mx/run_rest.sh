#!/usr/bin/env bash
cd "$(dirname "$0")"
./run_floppy.sh
echo "=== Falcon TOS 4.04 4MB HD"; python3 cold.py falcon 4096 4.04 build/mx_hd 500 native 0,16,32 2>&1 | tail -6
echo "=== Falcon EmuTOS"; python3 cold.py falcon 4096 emutos build/mx_hd 500 native 0 2>&1 | tail -6
echo DONE
