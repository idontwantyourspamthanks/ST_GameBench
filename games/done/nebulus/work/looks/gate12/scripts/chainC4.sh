#!/bin/bash
while [ ! -f /tmp/ng12hd/logs/core3/done ]; do sleep 20; done
cd /tmp/ng12hd/nb; export HOME=/tmp/ng12hd/home PYTHONUNBUFFERED=1 PYTHONPATH=/tmp/ng12hd/sc
python3 ikctl.py > /tmp/ng12hd/logs/core3/ik_ctl_mega.txt 2>&1; echo done > /tmp/ng12hd/logs/core3/done4
