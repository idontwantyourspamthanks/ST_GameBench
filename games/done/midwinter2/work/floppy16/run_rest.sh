#!/usr/bin/env bash
cd "$(dirname "$0")"
while pgrep -f "swapgate.py|bootgate.py|cell16.py" >/dev/null; do sleep 5; done
./batch_c.sh /tmp/mw2f/b16 s > out/batch_c.log 2>&1
./batch_b.sh /tmp/mw2f/b16 c > out/batch_b.log 2>&1
