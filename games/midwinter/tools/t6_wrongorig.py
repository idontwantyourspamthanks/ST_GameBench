#!/usr/bin/env python3
"""T6 builder: a patch set in which ONE site declares a wrong ORIGINAL (the tool's own verify is stubbed
out, since it would refuse to build).  The valid site comes first in the site table, so an all-or-nothing
trampoline must leave it unapplied too.

    python3 tools/t6_wrongorig.py          # writes build/t6 (game copy) and build/live/t6.{img,json}
"""
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mw1patch as m  # noqa: E402

tmp = Path(tempfile.mkdtemp(prefix="t6patches-"))
for n in ("core.s", "pp_nofade.s", "pp_bigram_cache.s", "test_boot_text.s"):
    shutil.copy(m.PATCHDIR / n, tmp / n)
(tmp / "zz_wrongorig.s").write_text(
    "; name: zz_wrongorig\n; site: $250f0\n; orig: 5354414343\n; phase: boot\n"
    "; note: declared orig 'STACC' but the game has 'STICK' at $250F0 (the Options label of control 2)\n"
    "        org     $250f0\n        dc.b    \"XXXXX\"\n")
m.PATCHDIR = tmp
m.cmd_verify = lambda *a, **k: 0
patches = m.load_patches()
print("patches:", [p.name for p in patches])
m.cmd_build(patches, m.ROOT / "build" / "t6", m.load_file_patches())
m.cmd_live(patches, m.ROOT / "build" / "live" / "t6")
