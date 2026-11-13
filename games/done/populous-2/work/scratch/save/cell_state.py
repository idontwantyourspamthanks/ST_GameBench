"""Evidence that the blob's TOS context is HAGA's own: the machine state at HAGA's own boot-time Fopen("P2D") trap (HAGA+$1020, the service's `trap #1`)
vs the state at the blob's first trap (fcreate, $80628) during an in-game SAVE.  Dumps SR / usp / ssp, the MFP enables, the vector table $0-$3ff and
the bytes at the game's entry $1770 (game code in game state, TOS data in TOS state)."""
import re, shutil, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sv import *

P = lambda *x: print(*x, flush=True)
tag = "state"
h, info = make("hd", "build/Pop2Save", "ste", None, 2048, tag)
OUT = SD / "out_state"; OUT.mkdir(exist_ok=True)


def arm_state(addr, nm):
    cf = SD / f"cmd_state_{nm}.txt"
    for f in ("vec", "g1770"):
        (OUT / f"{nm}_{f}.bin").unlink(missing_ok=True)
    cf.write_text(f"r\nm $fffffa07 2\nm $fffffa09 2\nm $fffffa13 2\nm $fffffa15 2\nsavebin {OUT}/{nm}_vec.bin $0 $400\nsavebin {OUT}/{nm}_g1770.bin $1770 32\n")
    h.cmd(f"hatari-debug b pc = ${addr:x} :trace :once :file {cf}")
    time.sleep(0.4)


def grab(nm, n0):
    L = h._logtext()[n0:]
    i = L.find(f"cmd_state_{nm}.txt")
    seg = L[i:]
    reg = re.findall(r"(SR=\w+.*?IM=\d)", seg)
    ier = re.findall(r"> m \$fffffa(\w+) 2\n\w+: (\w\w) ", seg)
    usp = re.findall(r"USP\s+(\w+)\s+ISP\s+(\w+)", seg)
    pc = re.findall(r"\n(\w{8}) \w{4}.*?\n", seg)
    return reg[:1], ier, usp[:1], seg


try:
    n0 = len(h._logtext())
    arm_state(0x1f9020, "haga")             # HAGA's service Fopen (P2D) at boot, 2 MB: base $1f8000 + $1020
    ok = h.boot_to_game(); P("boot", ok, h.marker(), turn(h))
    time.sleep(3)
    r = grab("haga", n0)
    P("HAGA's own Fopen(P2D) trap: SR/IM:", r[0], "usp/isp:", r[2], "MFP IER/IMR:", r[1])
    n1 = len(h._logtext())
    arm_state(blob_labels()["_traps"][1], "blob")      # the Fcreate trap in fcreate
    assert open_req(h); choose(h, "save"); name(h, "t1"); confirm(h)
    wait_running(h)
    r2 = grab("blob", n1)
    P("blob's Fcreate trap:         SR/IM:", r2[0], "usp/isp:", r2[2], "MFP IER/IMR:", r2[1])
    va = (OUT / "haga_vec.bin").read_bytes(); vb = (OUT / "blob_vec.bin").read_bytes()
    diff = [i for i in range(0, 0x400, 4) if va[i:i + 4] != vb[i:i + 4]]
    P(f"vector table $0-$3ff: HAGA-trap vs blob-trap: {len(diff)} of 256 longs differ", [(hex(i), va[i:i+4].hex(), vb[i:i+4].hex()) for i in diff[:12]])
    P("$70 at HAGA's trap:", va[0x70:0x74].hex(), " at the blob's trap:", vb[0x70:0x74].hex(), "(game state would be 000018fa)")
    P("$84 (trap #1) :", va[0x84:0x88].hex(), vb[0x84:0x88].hex(), "  $404 etv_critic:", va[0x404:0x408].hex() if len(va) > 0x404 else "")
    ga = (OUT / "haga_g1770.bin").read_bytes(); gb = (OUT / "blob_g1770.bin").read_bytes()
    P("bytes at $1770 at HAGA's trap:", ga.hex(), "\n                at blob's trap :", gb.hex(), "\n  game code at $1770 (P2M.FIC unpacked) starts 33f90000202800039...: low RAM $1770 holds TOS data, not the game, in both")
    bad = logbad(h); P("log errors:", len(bad))
finally:
    shutil.copy(h.logpath, SD / f"{tag}.log")
    h.close()
