"""PopTTPtr test scaffolding (not shipped): TT / Falcon floppy cold boot, START GAME or NEW GAME route to play, and the per-VBL pointer-visibility sampler.

Metric (all raw in the Hatari log): at every entry of the game's VBL routine ($16d70 + D) the debugger prints the video base ($ff8201/03), the address of the
last pointer draw ($16f12 + D), the two buffer variables $3c50c/$3c510 and `info video` (VBL counter).  The frame that just ended showed the buffer at the video base
(the flip writes the base right after the VBL routine); it showed the pointer iff $16f12 lies inside that buffer.
"""
import re, subprocess, sys, time
from pathlib import Path
GP = Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous")
ROOT = GP.parent.parent.parent
sys.path[:0] = [str(ROOT / "tools"), str(GP / "tools"), str(GP / "work/scratch/machines")]
import mm, pm_cells as pc            # noqa: E402
from PIL import Image               # noqa: E402

SH = GP / "work/shots/ttptr"
MENU = pc.REF / "tt_menu_buttons.png"
MBOX = (460, 310, 640, 395)
NEWGAME_XY = (475, 350)
START_XY = (175, 350)


def shot(h, name, tries=4):
    f = str(SH / name)
    for _ in range(tries):
        try:
            h.shot(f)
            time.sleep(0.4)
            return f
        except Exception:
            time.sleep(1)
    return None


def boot(cell, path, extra=(), mem=None, tos=None, timeout=240):
    """Cold boot a floppy image; return (h, seconds until the menu) ."""
    h = mm.start(cell, "floppy", str(path), extra=list(extra), mem=mem, tos=tos)
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(1.0)
        try:
            p = str(h.R / "cur.png")
            h.shot(p)
            time.sleep(0.3)
            if pc.crop_match(p, MENU if cell == "tt" else pc.REF / "falcon_menu_buttons.png",
                             MBOX if cell == "tt" else (500, 310, 680, 395), 14):
                return h, time.time() - t0
        except Exception:
            pass
    return h, None


def to_play(h, cell, route):
    """menu -> CONQUEST -> world page -> START GAME | NEW GAME + typed name + START GAME -> play.  Returns D."""
    pc.goto_shot(h, cell, "menu", *pc.CONQUEST)
    h.click(hold=0.4)
    sref = pc.REF / ("tt_start_page.png" if cell == "tt" else "falcon_start_page.png")
    (gx, gy), _ = pc.GEOM[(cell, "game")]
    sbox = (60 + gx, 105 + gy, 340 + gx, 225 + gy)
    t = pc.wait_for_crop(h, sref, sbox, 180)
    if t is None:
        raise RuntimeError("start page not reached")
    time.sleep(2)
    if route == "new":
        pc.goto_shot(h, cell, "game", *NEWGAME_XY)
        h.click(hold=0.4)
        time.sleep(3)
        for c in "genesis":
            h.key(c, 0.35)
            time.sleep(0.6)
        time.sleep(1)
        h.keypress(28)
        time.sleep(4)
    pc.goto_shot(h, cell, "game", *START_XY)
    h.click(hold=0.4)
    time.sleep(12)
    D = pc.delta(h)
    return D


def arm(h, D, name="vs"):
    f = h.R / f"{name}.txt"
    f.write_text("m $ff8201 1\nm $ff8203 1\nm $%x 4\nm $%x 8\ninfo video\n" % (0x16F12 + D, 0x3C50C + D))
    h.debug("b all", 0.3)
    s = len(h._logtext())
    h.cmd(f"hatari-debug b pc = ${0x16D70 + D:x} :trace :file {f}")
    return s


def disarm(h):
    h.debug("b all", 0.4)


REC = re.compile(r"> m \$ff8201 1\n00FF8201: (\w\w).*\n> m \$ff8203 1\n00FF8203: (\w\w).*\n> m \$\w+ 4\n\w+: (\w\w) (\w\w) (\w\w) (\w\w).*\n"
                 r"> m \$\w+ 8\n\w+: (\w\w) (\w\w) (\w\w) (\w\w) (\w\w) (\w\w) (\w\w) (\w\w).*\n> info video\nVideo base   : 0x(\w+)\nVBL counter  : (\d+)")


def parse(text):
    out = []
    for m in REC.finditer(text):
        g = m.groups()
        base = (int(g[0], 16) << 16) | (int(g[1], 16) << 8)
        f12 = int("".join(g[2:6]), 16)
        c50c = int("".join(g[6:10]), 16)
        c510 = int("".join(g[10:14]), 16)
        out.append(dict(vbl=int(g[15]), base=base, f12=f12, c50c=c50c, c510=c510))
    return out


def stats(recs):
    """frames = consecutive VBL pairs; visible = the pointer's last draw lies in the buffer at the video base."""
    vis = n = flips = 0
    for a, b in zip(recs, recs[1:]):
        if b["vbl"] != a["vbl"] + 1:
            continue
        n += 1
        if b["base"] <= b["f12"] < b["base"] + 32000:
            vis += 1
        if b["base"] != a["base"]:
            flips += 1
    return dict(frames=n, visible=vis, flips=flips)


def measure(h, D, secs=6, move=False, name="vs", shots=None):
    s = arm(h, D, name)
    t0 = time.time()
    k = 0
    while time.time() - t0 < secs:
        if move:
            h.rel(20 if k % 2 == 0 else -20, 0, 4)
            k += 1
        else:
            time.sleep(0.5)
        if shots and k % 2 == 0:
            pass
    disarm(h)
    time.sleep(0.5)
    recs = parse(h._logtext()[s:])
    return stats(recs), recs


# ---- double-pointer / pointer-presence check on dumped buffers ----------------------------------------------------------------
import numpy as np


def decode(buf):
    """32000 bytes of ST low -> 200 x 320 array of 4-bit colour indices."""
    a = np.frombuffer(buf, dtype=">u2").reshape(200, 20, 4).astype(np.uint16)
    out = np.zeros((200, 320), dtype=np.uint8)
    for b in range(16):
        bits = (a >> (15 - b)) & 1
        out[:, b::16] = bits[:, :, 0] | (bits[:, :, 1] << 1) | (bits[:, :, 2] << 2) | (bits[:, :, 3] << 3)
    return out


def sprite_pixels(sheet, idx_table, shape):
    """opaque pixels (dx, dy, colour) of the pointer shape: 16 rows x (mask word + 4 plane words); mask bit 1 = keep the background.
    `sheet` is the 160 bytes of that shape."""
    off = 0
    px = []
    for r in range(16):
        w = [int.from_bytes(sheet[off + r * 10 + 2 * k:off + r * 10 + 2 * k + 2], "big") for k in range(5)]
        for b in range(16):
            if not (w[0] >> (15 - b)) & 1:
                c = sum(((w[1 + k] >> (15 - b)) & 1) << k for k in range(4))
                px.append((b, r, c))
    return px


def find_sprite(img, px, xmax=300, ymax=180):
    """positions (x, y) where every opaque sprite pixel of the shape matches the screen."""
    ok = np.ones((ymax, xmax), dtype=bool)
    for dx, dy, c in px:
        ok &= img[dy:dy + ymax, dx:dx + xmax] == c
    ys, xs = np.nonzero(ok)
    return [(int(x), int(y)) for y, x in zip(ys, xs)]


def _hexbytes(txt, addr, n):
    m = re.findall(r"^%08X:\s+((?:[0-9A-Fa-f]{2} )+)" % addr, txt, re.M)
    return bytes.fromhex("".join(m).replace(" ", "")) if m else b""


def rdmem(h, addr, n):
    out = b""
    while len(out) < n:
        k = min(16 * 16, n - len(out))
        t = h.debug(f"m ${addr + len(out):x} {k}", 0.5)
        got = []
        for ln in t.splitlines():
            mm_ = re.match(r"^([0-9A-F]{8}):\s+((?:[0-9a-f]{2} )+)", ln)
            if mm_ and int(mm_.group(1), 16) >= addr + len(out):
                got.append(bytes.fromhex(mm_.group(2).replace(" ", "")))
        out += b"".join(got)[:k]
    return out


_SHAPES = {}


def shape_bytes(h, D, shape):
    if shape not in _SHAPES:
        sheet_ptr = int.from_bytes(rdmem(h, 0x3D572 + D, 4), "big")
        idx = int.from_bytes(rdmem(h, 0x22B06 + D + 2 * shape, 2), "big")
        _SHAPES[shape] = rdmem(h, sheet_ptr + idx * 160, 160)
    return _SHAPES[shape]


def sample_dump(h, D, n=10, label="dd", gap=0.2):
    """n once-breakpoints at the VBL entry; each saves both buffers + the pointer variables.  Returns [(vars, bufA, bufB)]"""
    bufs = get_bufs(h, D)
    res = []
    for k in range(n):
        base = h.R / f"{label}{k}"
        f = h.R / f"{label}{k}.cmd"
        f.write_text(f"savebin {base}_a.bin ${bufs[0]:x} 32000\nsavebin {base}_b.bin ${bufs[1]:x} 32000\nm $ff8201 1\nm $ff8203 1\nm ${0x16F12 + D:x} 4\n"
                     f"m ${0x24786 + D:x} 4\nm ${0x2169A + D:x} 2\nm ${0x16D26 + D:x} 2\nm ${0x3C50C + D:x} 8\nm ${0x16D28 + D:x} 2\nsavebin {base}_done.bin $0 2\n")
        for p in (Path(str(base) + "_done.bin"),):
            if p.exists():
                p.unlink()
        h.debug("b all", 0.2)
        s = len(h._logtext())
        h.cmd(f"hatari-debug b pc = ${0x16D70 + D:x} :trace :once :file {f}")
        t0 = time.time()
        while not Path(str(base) + "_done.bin").exists():
            if time.time() - t0 > 20:
                raise TimeoutError("dump bp")
            time.sleep(0.1)
        time.sleep(0.3)
        txt = h._logtext()[s:]
        g = re.findall(r"00FF8201: (\w\w)", txt) + re.findall(r"00FF8203: (\w\w)", txt)
        bs = (int(g[0], 16) << 16) | (int(g[1], 16) << 8)
        f12 = int.from_bytes(bytes.fromhex(re.search(r"%08X: (\w\w) (\w\w) (\w\w) (\w\w)" % (0x16F12 + D), txt).group(0)[10:].replace(" ", "")), "big")
        xy = bytes.fromhex(re.search(r"%08X: ((?:\w\w ){4})" % (0x24786 + D), txt).group(1).replace(" ", ""))
        shp = int.from_bytes(bytes.fromhex(re.search(r"%08X: (\w\w \w\w)" % (0x2169A + D), txt).group(1).replace(" ", "")), "big")
        hid = int.from_bytes(bytes.fromhex(re.search(r"%08X: (\w\w \w\w)" % (0x16D26 + D), txt).group(1).replace(" ", "")), "big")
        vv = re.search(r"%08X: ((?:\w\w ){8})" % (0x3C50C + D), txt).group(1).split()
        c50c_, c510_ = int("".join(vv[:4]), 16), int("".join(vv[4:]), 16)
        flag = int(re.search(r"%08X: (\w\w \w\w)" % (0x16D28 + D), txt).group(1).replace(" ", ""), 16)
        A = Path(str(base) + "_a.bin").read_bytes(); B = Path(str(base) + "_b.bin").read_bytes()
        shown, other = (A, B) if bs == bufs[0] else (B, A)
        pos_s = find_any(h, D, decode(shown)); pos_o = find_any(h, D, decode(other))
        res.append(dict(c50c=c50c_, c510=c510_, flag=flag, base=bs, f12=f12, x=int.from_bytes(xy[:2], "big"), y=int.from_bytes(xy[2:], "big"), shape=shp, hidden=hid, shown=pos_s, other=pos_o))
        time.sleep(gap)
    h.debug("b all", 0.2)
    return res


def dump_at(h, D, pcaddr, label, bufs, shp=1):
    """one once-breakpoint at pcaddr: dump both buffers + f12; returns dict (pointer positions in each buffer)."""
    base = h.R / label
    f = h.R / f"{label}.cmd"
    done = Path(str(base) + "_done.bin")
    if done.exists():
        done.unlink()
    f.write_text(f"savebin {base}_a.bin ${bufs[0]:x} 32000\nsavebin {base}_b.bin ${bufs[1]:x} 32000\nm $ff8201 1\nm $ff8203 1\nm ${0x16F12 + D:x} 4\ninfo video\nsavebin {base}_done.bin $0 2\n")
    h.debug("b all", 0.2)
    s = len(h._logtext())
    h.cmd(f"hatari-debug b pc = ${pcaddr:x} :trace :once :file {f}")
    t0 = time.time()
    while not done.exists():
        if time.time() - t0 > 20:
            raise TimeoutError("dump_at")
        time.sleep(0.05)
    time.sleep(0.3)
    txt = h._logtext()[s:]
    b1 = re.search(r"00FF8201: (\w\w)", txt).group(1); b3 = re.search(r"00FF8203: (\w\w)", txt).group(1)
    f12 = int("".join(re.search(r"%08X: (\w\w) (\w\w) (\w\w) (\w\w)" % (0x16F12 + D), txt).groups()), 16)
    vbl = int(re.search(r"VBL counter  : (\d+)", txt).group(1)); hbl = int(re.search(r"HBL line     : (\d+)", txt).group(1))
    A = Path(str(base) + "_a.bin").read_bytes(); B = Path(str(base) + "_b.bin").read_bytes()
    return dict(vbl=vbl, hbl=hbl, base=(int(b1, 16) << 16) | (int(b3, 16) << 8), f12=f12, A=find_any(h, D, decode(A)), B=find_any(h, D, decode(B)))


def find_any(h, D, img, shapes=range(7)):
    """[(shape, x, y)] for every pointer shape 0..6 found anywhere (y <= 180).  Shape 7 is left out: it matches static dialog art ((216, 128..140) in the GAME LOST dialog, also in unpatched runs)."""
    out = []
    for shp in shapes:
        px = sprite_pixels(shape_bytes(h, D, shp), None, shp)
        out += [(shp, x, y) for x, y in find_sprite(img, px)]
    return out


def frames_dump(h, D, bufs, nframes=4, ahead=40, events=("VBL", "BASEW"), extra=()):
    """arm once-breakpoints for every (event, VBL = N..N+nframes-1) at once; returns the dumps in time order."""
    cur = h.vbl()
    N = cur + ahead
    evpc = {"VBL": 0x16D70 + D, "BASEW": 0x16F34 + D, "HOOKEND": 0xB8000 + 0x2e}
    evpc.update(dict(extra))
    names = []
    h.debug("b all", 0.2)
    for k in range(nframes):
        for ev in events:
            base = h.R / f"fd_{ev}_{k}"
            done = Path(str(base) + "_done.bin")
            if done.exists():
                done.unlink()
            f = h.R / f"fd_{ev}_{k}.cmd"
            f.write_text(f"savebin {base}_a.bin ${bufs[0]:x} 32000\nsavebin {base}_b.bin ${bufs[1]:x} 32000\nm $ff8201 1\nm $ff8203 1\nm ${0x16F12 + D:x} 4\ninfo video\nsavebin {base}_done.bin $0 2\n")
            h.cmd(f"hatari-debug b pc = ${evpc[ev]:x} && VBL = {N + k} :trace :once :file {f}")
            names.append((ev, k, base, done))
    t0 = time.time()
    while not all(d.exists() for *_, d in names):
        if time.time() - t0 > 90:
            break
        time.sleep(0.2)
    time.sleep(0.5)
    txt = h._logtext()
    out = []
    for ev, k, base, done in names:
        if not done.exists():
            out.append((ev, k, None)); continue
        A = Path(str(base) + "_a.bin").read_bytes(); B = Path(str(base) + "_b.bin").read_bytes()
        out.append((ev, k, dict(A=find_any(h, D, decode(A)), B=find_any(h, D, decode(B)))))
    h.debug("b all", 0.2)
    return out, txt


def get_bufs(h, D):
    """the two screen buffers, from the VBL sampler (a plain read of $3c50c / $3c510 can land between the two halves of the game's swap and return the same value twice)."""
    s, recs = measure(h, D, secs=1.5, name="gb")
    vals = set()
    for r in recs:
        vals |= {r["c50c"], r["c510"]}
    vals = sorted(v for v in vals if v)
    assert len(vals) == 2, vals
    return vals
