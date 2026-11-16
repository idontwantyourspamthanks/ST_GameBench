#!/bin/sh
# dis.sh START [END]  (disassemble from the pass-start RAM dump)
python3 /home/ryan/Code/AtariST/gamebench/tools/m68dis.py /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/extrap/h_start_7a88.bin $1 ${2:+--end $2}
