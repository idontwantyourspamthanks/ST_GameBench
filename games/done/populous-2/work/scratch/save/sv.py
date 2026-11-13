"""Populous 2 in-game SAVE/LOAD test library (gates for patches/pop2_save*.s).

Cells are cold boots of a build (HD folder through Hatari's GEMDOS drive, an own ACSI + HDDRIVER image, or a 720K floppy) driven through the
game's own requester.  Evidence is taken with debugger breakpoints that dump $39630..+56690 at the instant of the write call ($80300 with d0 = 1)
and right after the read returned ($2cc5e), so "RAM equals the saved state" is a byte compare, not a screenshot.
"""
import filecmp, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

G = Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2")
SD = G / "work/scratch/save"
sys.path[:0] = [str(G / "tools"), "/home/ryan/Code/AtariST/gamebench/tools"]
from populous2 import Populous2, HOME          # noqa: E402
from stharness import TOS                       # noqa: E402

SIZE = 56690
BAD = re.compile(r"bus error|address error|exception [23] |halt|double|illegal", re.I)
PREFETCH = re.compile(r"^Prefetch ")
# PP's boot-time hardware probes (RUNME / HAGA: TT, blitter, STE registers), also in the stock game (work/notes/release.md)
PROBE = re.compile(r"Bus Error reading at address \$(ffff8e21|ffff8924|ffff8781|fff000[0-9a-f]{2})\b")
TURN = 0x3979C


def make(media="hd", build="build/Pop2Save", machine="ste", tos=None, mem=2048, tag="x", overlay=None, img=None, prot=False, extra=(), second=None, size_mb=16, leave=None, disk_a=None, snapshot=None):
    """-> (Populous2, info dict).  media: hd (Hatari GEMDOS drive C), acsi (own HDDRIVER image; `img` reuses one), floppy (720K in A:, `img` = .st)."""
    extra = list(extra)
    if machine == "tt":
        extra += ["--mmu", "true", "--monitor", "vga", "--cpuclock", "32"]
    kw = dict(machine=machine, memsize_kb=mem)
    if snapshot:
        kw["snapshot"] = str(snapshot)
    if tos:
        kw["tos"] = TOS[tos]
    info = {"media": media, "machine": machine, "tos": tos or "default", "mem": mem}
    if media == "hd":
        kw.update(game_dir=G / build)
        if disk_a:
            extra += ["--disk-a", str(disk_a)]
            if prot:
                extra += ["--protect-floppy", "on"]
        if overlay:
            kw["overlay"] = Path(overlay)
    elif media == "acsi":
        sys.path.insert(0, str(G.parent / "hunter/tools"))
        from hunter import build_hd
        R = Path(tempfile.mkdtemp(prefix="strun-"))
        if img:
            shutil.copy(img, R / "hd.img")
        else:
            build_hd(R / "hd.img", G / build, size_mb, "C:\\RUNME.TOS")
            if leave is not None:                 # fill the partition so that only `leave` bytes remain free
                md = subprocess.run(["mdir", "-i", f"{R/'hd.img'}@@1024", "::"], capture_output=True, text=True).stdout
                free = int(re.findall(r"([\d ]+) bytes free", md)[-1].replace(" ", ""))
                (R / "filler.dat").write_bytes(b"\0" * max(0, free - leave - 2048))
                subprocess.run(["mcopy", "-i", f"{R/'hd.img'}@@1024", str(R / "filler.dat"), "::FILLER.DAT"], check=True)
        bus = "ide" if machine == "falcon" else "acsi"
        hd = {"acsi": ["--acsi", f"0={R/'hd.img'}"], "ide": ["--ide-master", str(R / "hd.img")]}[bus]
        kw.update(game_dir=G / build, files=[], autorun="", workdir=str(R))
        extra += ["--gemdos-drive", "skip"] + hd
        info["img"] = str(R / "hd.img")
        if disk_a:
            extra += ["--disk-a", str(disk_a)]
            if prot:
                extra += ["--protect-floppy", "on"]
    elif media == "floppy":
        st = Path(tempfile.mkdtemp(prefix="p2sv-")) / "boot.st"
        shutil.copy(img or (G / build / "Populous2_boot.st"), st)
        kw.update(game_dir=G / "originals/POPUL2", files=[], autorun="")
        extra += ["--disk-a", str(st)]
        if second:
            extra += ["--disk-b", str(second)]
        if prot:
            extra += ["--protect-floppy", "on"]
        info["st"] = str(st)
    h = Populous2(extra=extra, **kw)
    return h, info


def turn(h):
    return h.peekw(TURN)


def frozen(h, wait=1.5):
    a = turn(h); time.sleep(wait); return turn(h) == a


def running(h, wait=1.5):
    return not frozen(h, wait)


def wait_running(h, timeout=90):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if running(h, 1.2):
            return True
    return False


def open_req(h):
    """strip icon 1 = the game requester; the world stops while it is up"""
    for _ in range(4):
        h._click(707, 374, 3)
        if frozen(h):
            return True
        time.sleep(1)
    return False


def choose(h, kind):
    h._click(535 if kind == "save" else 318, 178, 4)


def field(h, y, text, clear=14):
    h._click(470, y, 0.8)
    for _ in range(clear):
        h.key("BackSpace", 0.15)
    for ch in text:
        if ch == ":":
            h.key("shift+semicolon", 0.3)
        elif ch == "\\":
            h.key("backslash", 0.3)
        else:
            h.key(ch.lower(), 0.3)
        time.sleep(0.3)
    h.key("Return", 0.3); time.sleep(1)


def name(h, text):
    field(h, 370, text)


def drawer(h, text):
    field(h, 338, text, 24)


def confirm(h):
    h._click(288, 418, 1)


def cancel(h):
    h._click(560, 418, 2)


def arm(h, addr, out, cond="", n=SIZE, tag=""):
    """a one-shot breakpoint at pc = addr that dumps the save area to `out`"""
    out = Path(out); out.unlink(missing_ok=True)
    cf = SD / f"cmd_{addr:x}_{tag or out.stem}.txt"
    cf.write_text(f"savebin {out} $39630 {n}\nr\n")
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b pc = ${addr:x} {cond} :trace :once :file {cf}")
    t0 = time.time()
    while time.time() - t0 < 15 and "breakpoint" not in h._logtext()[n0:]:
        time.sleep(0.3)
    time.sleep(0.4)


def disarm(h):
    h.debug("b all", 0.4)


def waitfile(p, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if Path(p).exists() and Path(p).stat().st_size == SIZE:
            time.sleep(0.3); return True
        time.sleep(0.5)
    return False


def logbad(h):
    return [l for l in h._logtext().splitlines() if BAD.search(l) and not PREFETCH.search(l) and not PROBE.search(l)]


def hdfile(h, n):
    """the saved file on the Hatari GEMDOS drive"""
    return h.R / "C" / "FILES" / n


def imgfile(img, n, sub="FILES"):
    """read a file out of the ACSI image (HDDRIVER partition at sector 2); None if absent"""
    r = subprocess.run(["mtype", "-i", f"{img}@@1024", f"::{sub}/{n}" if sub else f"::{n}"], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def shot(h, nm):
    p = SD / nm; h.shot(str(p)); return p


def blob_labels(patch="pop2_save", seg_org=0x80400):
    """label -> payload address of part B of the blob (assembled like pop2patch does, plus a listing); B runs at HAGA+$3900+$d00"""
    import pop2patch as PP
    p = [x for x in PP.load_patches() if x.name == patch][0]
    seg = [s for s in p.segments if s[0] == seg_org][0]
    src = PP.equ_preamble() + "\n" + "\n".join(p.preamble) + f"\n\torg\t${seg_org:x}\n" + "\n".join(seg[1]) + "\n"
    td = Path(tempfile.mkdtemp(prefix="p2lbl-"))
    (td / "s.s").write_text(src)
    subprocess.run([PP.VASM, "-Fbin", "-m68000", "-quiet", "-L", str(td / "s.lst"), "-o", str(td / "s.bin"), str(td / "s.s")], check=True)
    out = {}
    lst = (td / "s.lst").read_text()
    for m in re.finditer(r"^(\w+)\s+A:([0-9A-Fa-f]{8})\s*$", lst, re.M):
        out[m.group(1)] = int(m.group(2), 16)
    out["_traps"] = [int(m.group(1), 16) for m in re.finditer(r"^00:([0-9A-F]{8}) 4E41", lst, re.M)]
    out["_len"] = (td / "s.bin").stat().st_size
    shutil.rmtree(td, ignore_errors=True)
    return out


def blob_runtime(h, addr, seg_org=0x80400):
    """runtime address of a part-B payload address: HAGA base ($328) + $3900 (block) + $d00 (code) + offset in B"""
    base = h.peekl(0x328)
    return base + 0x3900 + 0xd00 + (addr - seg_org)
