#!/bin/bash
export HOME=/tmp/ng12fl/home
while pgrep -f chain3.sh >/dev/null; do sleep 20; done
cd /tmp/ng12fl/s
python3 docs2.py /tmp/ng12fl/game.st /tmp/ng12fl/w_docs2 /tmp/ng12fl/campaign_disk.st ste > /tmp/ng12fl/out/docs2b.txt 2>&1
echo done > /tmp/ng12fl/out/chain4.done
