#!/usr/bin/env bash
# reruns of the single-drive pairs whose first version waited for the M/J/K screen without pressing keys (the intro screens want keys)
cd "$(dirname "$0")"
while pgrep -f "run_rest.sh" >/dev/null; do sleep 10; done
D=${1:-/tmp/mw2f/b16}
for spec in "s_ste_d1_v16 A B" "s_ste_d1_v16c C CB"; do
  set -- $spec; n=$1; shift
  timeout 900 python3 swapgate.py "$n" ste 162 8 1 $D "$@" > "out/$n.log" 2>&1; grep SWAP "out/$n.log" | tee -a out/rerun_c.log
done
