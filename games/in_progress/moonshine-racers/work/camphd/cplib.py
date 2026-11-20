"""Shared helpers of the HD campaign gate scripts (scratch).  Import after env.sh (private HOME)."""
import os, re, struct, sys, time, shutil, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
G = HERE.parents[1]
sys.path.insert(0, str(G / "tools")); sys.path.insert(0, str(G.parents[2] / "tools"))
from msr import Moonshine
from stharness import TOS
import msrpatch as P

def log(*a):
    print(*a, flush=True)

def mem(h, addr, n):
    """m dump parsed to bytes (waits until the last line of the dump is in the log)."""
    n0 = len(h._logtext()); h.cmd(f"hatari-debug m ${addr:x} {n}")
    last = addr + ((n - 1) // 16) * 16
    t = time.time(); out = ""
    while time.time() - t < 8:
        time.sleep(0.15)
        out = h._logtext()[n0:]
        if re.search(rf"^{last:08x}:", out, re.I | re.M):
            time.sleep(0.1); out = h._logtext()[n0:]; break
    b = bytearray()
    for ln in out.splitlines():
        m = re.match(r"\s*([0-9a-fA-F]{8}):\s+((?:[0-9a-fA-F]{2} )*[0-9a-fA-F]{2})(?:  |$)", ln)
        if m and addr <= int(m.group(1), 16) < addr + n: b += bytes.fromhex(m.group(2).replace(" ", ""))
    return bytes(b[:n])

W = lambda b, o=0: struct.unpack(">H", b[o:o + 2])[0]
L = lambda b, o=0: struct.unpack(">I", b[o:o + 4])[0]

def cp_patches():
    """The campaign patches as (blobs [(addr, bytes)], sites [(addr, new bytes)]) assembled from patches/cp_*.s."""
    blobs, sites = [], []
    for p in P.load_patches():
        if not p.name.startswith("cp_"): continue
        orig, new = P.site_bytes(p)
        sites.append((p.site, new))
        for org, lines in p.segments:
            if org != p.site:
                blobs.append((org, P.assemble(org, lines, "\n".join(p.preamble))))
    return blobs, sites

def apply_live(h, scratch=None):
    """Load the campaign blobs and write the gated sites into a running snapshot (the title) of a build WITHOUT the campaign patches."""
    scratch = Path(scratch or tempfile.mkdtemp(prefix="cplive-"))
    blobs, sites = cp_patches()
    for i, (a, b) in enumerate(blobs):
        f = scratch / f"b{i}.bin"; f.write_bytes(b)
        h.debug(f"loadbin {f} ${a:x}", 0.5)
    for a, nb in sites:
        h.debug(f"w ${a:x} " + " ".join(f"${x:02x}" for x in nb), 0.4)
    return blobs, sites

def start(snapshot, game_dir, machine="ste", mem_kb=2048, tos=None, **kw):
    k = {"tos": TOS[tos]} if tos else {}
    return Moonshine(snapshot=str(snapshot), game_dir=str(game_dir), machine=machine, memsize_kb=mem_kb, **k, **kw)

def wait_vbl(h, n):
    v = h.vbl()
    while h.vbl() < v + n:
        time.sleep(0.5)
