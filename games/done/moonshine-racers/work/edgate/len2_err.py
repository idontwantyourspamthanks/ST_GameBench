#!/usr/bin/env python3
"""WP-B gate (--v11: the same files against a build without version 2, e.g. the old HD build: v2 refused, v1 loads): cp_title `validate` with the race length word (version 2): one HD session, every file loaded through the F10 menu (FILES\\MSTRACKS.TRK replaced between loads).
   envab.sh python3 len2_err.py --build DIR [--machine ste --mem 2048]
Files (all made here with the table CRC fixed up, so that ONLY the one rule under test can refuse them): good: len2.trk (v2), c3.trk (v1), v2 with words 700 / 28000 (the range ends), v2 with all words 0;
refused ('NOT A VALID'): v2 word 699, v2 word 28001, v2 word 65535, v1 file with a word, version 3, version 0."""
import argparse, sys, struct, zlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "campgate"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from cg import *
import msrtrack as M

ap = argparse.ArgumentParser(); ap.add_argument("--build", required=True); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=2048)
ap.add_argument("--v11", action="store_true", help="the build is the released v1.1 / the pre-version-2 loader: every version 2 file must be refused (its version check)"); a = ap.parse_args()
tag = f"len2_err{'_v11' if a.v11 else ''}_{a.machine}{a.mem // 1024}m"; logopen(tag)
FX = Path(__file__).resolve().parents[1] / "trackedit/fixtures/len2.trk"
f2 = FX.read_bytes(); f1 = (CAMP / "c3.trk").read_bytes()

def fix(b):
    """recompute the table CRC (bytes 0..11 + the entry table) of a patched campaign file"""
    b = bytearray(b); cnt = struct.unpack_from(">H", b, 6)[0]
    struct.pack_into(">L", b, 12, zlib.crc32(bytes(b[:12]) + bytes(b[16:16 + 40 * cnt]))); return bytes(b)

def patched(src, ver=None, words=None):
    b = bytearray(src)
    if ver is not None: struct.pack_into(">H", b, 4, ver)
    for i, w in (words or {}).items(): struct.pack_into(">H", b, 16 + 40 * i + 26, w)
    return fix(b)

blk0 = M.parse_campaign(f1)[0]
C = [  # name, bytes, expect: None = loads, else the message text
    ("v2_good_len2", f2, None), ("v1_good_c3", f1, None),
    ("v2_word700", patched(f2, words={0: 700}), None), ("v2_word28000", patched(f2, words={0: 28000}), None),
    ("v2_all_zero_words", patched(f2, words={0: 0, 1: 0, 2: 0, 3: 0, 4: 0}), None),
    ("v2_word699", patched(f2, words={1: 699}), "NOT A VALID"), ("v2_word28001", patched(f2, words={2: 28001}), "NOT A VALID"),
    ("v2_word65535", patched(f2, words={4: 65535}), "NOT A VALID"), ("v2_word32768_bit15", patched(f2, words={0: 32768}), "NOT A VALID"),
    ("v1_with_word", patched(f1, words={1: 2000}), "NOT A VALID"), ("v3", patched(f2, ver=3), "NOT A VALID"), ("v0", patched(f2, ver=0), "NOT A VALID"),
    ("v2_good_again", f2, None),
]
r = Run("hd", a.machine, a.mem, tag, build=a.build, camp_hd=FX)
host = r.h.R / "C" / "FILES" / "MSTRACKS.TRK"
def goto_item(n):
    for _ in range(8):
        s = r.w(0x100406)
        if s == n: return True
        r.key(0x50 if s < n else 0x48); time.sleep(0.6)
    return r.w(0x100406) == n
def do_load(wait=40):
    goto_item(1); texts_start(r); r.key(0x1c); t0 = time.time(); time.sleep(1)
    while time.time() - t0 < wait:
        if r.b(V["loaded"]): break
        if any(t[1] == 20 and t[2].strip() and "..." not in t[2] for t in texts_peek(r)): break
        time.sleep(0.3)
    time.sleep(1.5); tx = texts_stop(r)
    return r.b(V["loaded"]) != 0, [t[2] for t in tx if t[1] == 20]
try:
    r.ff(False)
    if not r.boot_title(): log("BOOT FAILED"); sys.exit(2)
    r.menu_open()
    for name, data, expect in C:
        if a.v11 and data[5] == 2 and expect is None: expect = "NOT A VALID"
        host.write_bytes(data)
        ok, tx = do_load()
        act = r.mem(V["act"], 4)
        log(f"CASE {name}: loaded={ok} message-row texts={tx} act={act[0]:#x} loaded={act[1]:#x} count={W(act, 2)}")
        if expect is None:
            check(f"{name}: loads (count {W(act, 2)})", ok and act[0] == 0xff and W(act, 2) == struct.unpack_from('>H', data, 6)[0])
            r.key(14); time.sleep(1.5)                                  # Backspace: the list back to the main menu
        else:
            check(f"{name}: rejected with a message", (not ok) and any(expect in x for x in tx), f"expect {expect!r}")
            check(f"{name}: campaign not armed", act[0] == 0 and act[1] == 0)
    log(f"Bus/Address error lines: {r.errlines()}")
finally:
    log(f"== {tag} done: {'ALL CHECKS PASS' if not FAILS else 'FAILED: ' + ', '.join(FAILS)}; bus/address error lines {r.errlines()}")
    r.close()
sys.exit(1 if FAILS else 0)
