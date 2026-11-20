"""Live patch helper: assemble vasm source segments, apply to a running Hatari via loadbin/w at a one-shot breakpoint."""
import subprocess, tempfile, time, re
from pathlib import Path

def assemble(org, src, equ="", syms=False):
    text = equ + f"\n\torg\t${org:x}\n" + src + "\n"
    with tempfile.TemporaryDirectory() as td:
        s = Path(td) / "seg.s"; s.write_text(text); o = Path(td) / "seg.bin"; lst = Path(td) / "seg.lst"
        r = subprocess.run(["vasmm68k_mot", "-Fbin", "-m68000", "-quiet", "-L", str(lst), "-o", str(o), str(s)], capture_output=True, text=True)
        if r.returncode: raise SystemExit(f"vasm failed:\n{text}\n{r.stderr}{r.stdout}")
        if not syms: return o.read_bytes()
        d = {}
        txt = lst.read_text().split("Symbols by name:")[1].split("Symbols by value:")[0]
        for ln in txt.splitlines():
            m = re.match(r"^(\S+)\s+[AE]:([0-9A-Fa-f]+)", ln)
            if m: d[m.group(1)] = int(m.group(2), 16)
        return o.read_bytes(), d

def apply_live(h, blobs, sites, at_pc=0x7a88, timeout=60):
    """blobs: [(addr, bytes)], sites: [(addr, newbytes)]. Applied at the next hit of `pc = at_pc`."""
    cmds = []
    for i, (a, b) in enumerate(blobs):
        p = h.R / f"blob{i}.bin"; p.write_bytes(b)
        cmds.append(f"loadbin {p} ${a:x}")
    for a, nb in sites:
        for k in range(0, len(nb), 8):
            cmds.append(f"w ${a + k:x} " + " ".join(f"${x:02x}" for x in nb[k:k + 8]))
    f = h.R / "apply.txt"; f.write_text("\n".join(cmds) + "\n")
    start = len(h._logtext())
    h.cmd(f"hatari-debug b pc = ${at_pc:x} :trace :once :file {f}")
    t = time.time()
    while "Removed CPU breakpoint" not in h._logtext()[start:]:
        if time.time() - t > timeout: raise TimeoutError("apply breakpoint never hit")
        time.sleep(0.2)
    time.sleep(0.4)
    return h._logtext()[start:]
