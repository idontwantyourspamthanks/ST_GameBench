#!/bin/bash
cd /tmp/looksgate/games/in_progress/nebulus; L=/tmp/looksgate/logs; R=/tmp/looksgate/r
for run in old1 new1 old2 new2; do b=${run%?}; python3 work/looks/run_look.py /tmp/looksgate/b_$b $R/stock_$run 8 stock ste > $L/c1_$run.log 2>&1; done
echo done > $L/c1.done
