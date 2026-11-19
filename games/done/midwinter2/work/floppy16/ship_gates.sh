#!/usr/bin/env bash
# Gate (d): the shipped zip.  usage: ship_gates.sh dist/Midwinter2_v1.6_patched_floppies_<date>.zip
# Unzips into /tmp/mw2f/ship, checks .st == .msa == the dev build, then runs gates (a), (c), (b) on the SHIPPED images (names prefix sg_ / sc_ / sb_).
set -euo pipefail
cd "$(dirname "$0")"
ZIP=$(readlink -f "$1")
rm -rf /tmp/mw2f/ship && mkdir -p /tmp/mw2f/ship && (cd /tmp/mw2f/ship && unzip -oq "$ZIP" && md5sum * > ../ship.md5 && cat ../ship.md5)
python3 - <<'P'
import sys; sys.path.insert(0, '../../tools')
import mw2patch as M
for n in ('FFA_boot', 'FFB_graphics', 'FFC_missions', 'FFD_campaign_blank'):
    st = open(f'/tmp/mw2f/ship/{n}.st', 'rb').read(); ms = open(f'/tmp/mw2f/ship/{n}.msa', 'rb').read()
    assert M.msa_to_st(ms) == st, n
print('shipped .msa == shipped .st (independent MSA reader): 4/4')
P
./batch_a.sh /tmp/mw2f/ship sg
./batch_c.sh /tmp/mw2f/ship sc
./batch_b.sh /tmp/mw2f/ship sb
timeout 1500 python3 cell16.py sb_ste162_8_d1_msa ste 162 1024 /tmp/mw2f/ship 8 1 --ext msa > out/sb_ste162_8_d1_msa.log 2>&1 || true
grep -E "^(CELL|EXC)|REACHED|first game restore|game type I commands" out/sb_ste162_8_d1_msa.log | cut -c1-240
