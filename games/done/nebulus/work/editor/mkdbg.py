#!/usr/bin/env python3
"""Debug variant of patches/ed_editor.s: records the raw GEMDOS results of the disk excursion in V+176 (Fopen), V+180 (Fread/Fwrite, last), V+184 (Fclose)
and moves `mchg` into CODE3 to make room.  Writes /tmp/ne/ed_dbg_src.s; build: ./dbgbuild.sh /tmp/ne/gdbg /tmp/ne/ed_dbg_src.s"""
from pathlib import Path
G = Path(__file__).resolve().parents[2]
s = (G / "patches/ed_editor.s").read_text()
a = s.index("mchg:   tst.w"); b = s.index("tos_io: move.w")
m = s[a:b]; s = s[:a] + s[b:]
s = s.replace("; result messages (status number = string number)\n", "; ---- debug: mchg moved\n" + m + "\n; result messages (status number = string number)\n", 1)
a = s.index("tos_io: move.w"); b = s.index("rw:     move.l  a0,-(a7)")
t = s[a:b]
t = t.replace("        tst.l   d0\n        bmi.s   .cls\n", "        move.l  d0,V+176.l\n        tst.l   d0\n        bmi.s   .cls\n", 1)
r = s[b:].replace("        trap    #1\n        lea     12(a7),a7\n        rts\n", "        trap    #1\n        lea     12(a7),a7\n        move.l  d0,V+180.l\n        rts\n", 1)
Path("/tmp/ne/ed_dbg_src.s").write_text(s[:a] + t + r)
