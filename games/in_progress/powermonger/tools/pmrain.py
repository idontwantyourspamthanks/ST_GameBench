#!/usr/bin/env python3
"""Rain-per-frame gate (work/notes/rain.md).  Captures every displayed frame at every main-loop top (`b pc=$12fd8`), decodes the
screen, and tests each frame for rain by RECOMPUTING the rain pattern: `$1a856` ORs a 32-bit table row (`$1a8a4` kind 1 / `$1a9c8` kind 2,
row = byte `$1aac8`-phase - 4 per scanline) into the back buffer, so a frame has rain iff for one of the 4 phases every set bit of the
predicted mask holds the rain colour.

    python3 tools/pmrain.py strip SNAP MHZ NFRAMES OUTDIR [--wx tick_wx|tick_rain] [--kind 1|2] [--tt DISK]
Env: PM_WX is set from --wx (pmtick.build_live reads it)."""
from __future__ import annotations
import argparse, os, sys, threading, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path[:0] = [str(GAME.parent.parent.parent / "tools"), str(HERE)]


def decode(buf: bytes) -> np.ndarray:
    """32000 B ST low-res planar -> (200,320) colour indices"""
    w = np.frombuffer(buf, dtype=">u2").reshape(200, 20, 4)
    bits = ((w[:, :, None, :] >> (15 - np.arange(16))[None, None, :, None]) & 1)      # row, group, bit, plane
    return (bits[..., 0] | bits[..., 1] << 1 | bits[..., 2] << 2 | bits[..., 3] << 3).reshape(200, 320)


def palette(raw: bytes, tt: bool) -> np.ndarray:
    v = np.frombuffer(raw[:32], dtype=">u2").astype(int)
    if tt:   # TT: 4 bits per component
        return np.stack([((v >> 8) & 15) * 17, ((v >> 4) & 15) * 17, (v & 15) * 17], 1).astype(np.uint8)
    f = lambda n: (((n & 7) << 1) | ((n >> 3) & 1)) * 17      # STE: bit 3 = LSB
    return np.stack([f(v >> 8), f(v >> 4), f(v)], 1).astype(np.uint8)


def mask_of(ram: bytes, kind: int, d3_0: int) -> np.ndarray:
    """(194,320) bool: pixels the rain call ORs, for first-row table index d3_0.  Rows 6..199, groups 4..19."""
    base = 0x1A8A4 if kind == 1 else 0x1A9C8
    d3 = (d3_0 - 4 * np.arange(194)) & 255
    L = np.array([int.from_bytes(ram[base + x: base + x + 4], "big") for x in d3], dtype=np.uint64)     # per row
    wlo, whi = (L & 0xFFFF).astype(np.uint16), (L >> 16).astype(np.uint16)
    words = np.stack([wlo if g % 2 == 0 else whi for g in range(16)], 1)                               # (194,16)
    bits = (words[:, :, None] >> (15 - np.arange(16))[None, None, :]) & 1
    m = np.zeros((194, 320), bool)
    m[:, 64:] = bits.reshape(194, 256).astype(bool)
    return m


def has_rain(ram: bytes, idx: np.ndarray, kind: int):
    """-> (best match fraction, d3_0) over every row-aligned phase (64 values), on rows 13..165 (3D window; the HUD is drawn over the rest), x >= 80"""
    rc = 15 if kind == 1 else 5
    sub = idx[6:200]
    win = np.zeros((194, 320), bool); win[13 - 6:166 - 6, 80:] = True
    best = (0.0, -1)
    for d3 in range(0, 256, 4):
        mm = mask_of(ram, kind, d3) & win
        n = int(mm.sum())
        f = float((sub[mm] == rc).sum()) / n if n else 0.0
        if f > best[0]:
            best = (f, d3)
    return best


def dump_frames(h, apply_cmds_, pokes, nframes, tt=False, mhz=8, settle=0):
    """Apply at a flip, then dump RAM + video regs at every loop top until `nframes` frames are captured.  -> list of (ram bytes, vid, pal)"""
    from pmtick import at_flip, wait_gone
    if mhz != 8:
        h.set_cpuclock(mhz)
    at_flip(h, list(pokes) + list(apply_cmds_))
    cur, vid, pal = h.R / "rcur.bin", h.R / "rvid.bin", h.R / "rpal.bin"
    f = h.R / "rdump.txt"
    LEN = 0x80000
    f.write_text(f"savebin {vid} $ff8200 $10\nsavebin {pal} {'$ff8400' if tt else '$ff8240'} $20\nsavebin {cur} $0 ${LEN:x}\n")
    got, stop = [], threading.Event()

    def poll():
        last = None
        while not stop.is_set():
            try:
                st = cur.stat()
            except FileNotFoundError:
                time.sleep(0.003); continue
            if st.st_size == LEN and st.st_mtime_ns != last:
                time.sleep(0.03)
                st2 = cur.stat()
                if st2.st_mtime_ns == st.st_mtime_ns and st2.st_size == LEN:
                    last = st.st_mtime_ns
                    got.append((cur.read_bytes(), vid.read_bytes(), pal.read_bytes()))
            time.sleep(0.004)
    th = threading.Thread(target=poll, daemon=True); th.start()
    h.debug("b all", 0.3)
    s2 = len(h._logtext())
    h.cmd(f"hatari-debug b pc = $12fd8 :trace :file {f}")
    t0 = time.time()
    while len(got) < nframes and time.time() - t0 < 600:
        time.sleep(0.2)
    h.debug("b all", 0.3)
    time.sleep(0.5)
    stop.set(); th.join()
    return got


def analyse(got, kind, outdir: Path, tag: str, tt=False):
    from PIL import Image
    outdir.mkdir(parents=True, exist_ok=True)
    rows, imgs = [], []
    for i, (ram, vid, pal) in enumerate(got):
        base = (vid[1] << 16) | (vid[3] << 8) | vid[0xD]
        base = base if base < 0x80000 else int.from_bytes(ram[0x2DF78:0x2DF7C], "big")
        idx = decode(ram[base:base + 32000])
        rgb = palette(pal, tt)[idx]
        tick = int.from_bytes(ram[0x4BB3E:0x4BB42], "big")
        k4 = int.from_bytes(ram[0x4BB42:0x4BB44], "big"); left = int.from_bytes(ram[0x4BB44:0x4BB46], "big", signed=True)
        f, d3 = has_rain(ram, idx, k4 if k4 in (1, 2) else kind)
        rows.append((i, tick, k4, left, hex(base), round(f, 3), d3))
        imgs.append(rgb)
    return rows, imgs


def montage(imgs, path, cols=4, crop=(80, 6, 320, 166), scale=1):
    from PIL import Image
    x0, y0, x1, y1 = crop
    w, h = x1 - x0, y1 - y0
    n = len(imgs); rws = (n + cols - 1) // cols
    M = Image.new("RGB", (cols * (w + 2), rws * (h + 2)), (255, 0, 255))
    for i, im in enumerate(imgs):
        t = Image.fromarray(im[y0:y1, x0:x1])
        M.paste(t, ((i % cols) * (w + 2), (i // cols) * (h + 2)))
    if scale != 1:
        M = M.resize((M.width * scale, M.height * scale), Image.NEAREST)
    M.save(path)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("strip"); s.add_argument("snap"); s.add_argument("mhz", type=int); s.add_argument("nframes", type=int); s.add_argument("outdir")
    s.add_argument("--wx", default="tick_rain"); s.add_argument("--kind", type=int, default=2); s.add_argument("--left", type=int, default=0x2000)
    s.add_argument("--poke", action="append", default=[], help="extra debugger command(s) at the apply flip; with --kind -1 the rain clock is not poked")
    s.add_argument("--orig", action="store_true", help="no tick patches at all (the unpatched game: per-frame world)")
    c = sub.add_parser("cold", help="cold boot a built floppy to the 3D map, force rain, capture consecutive frames (STE/ST/TT)")
    c.add_argument("disk"); c.add_argument("nframes", type=int); c.add_argument("outdir"); c.add_argument("--machine", default="tt"); c.add_argument("--tos", default="3.06")
    c.add_argument("--mem", type=int, default=4096); c.add_argument("--mhz", type=int, default=0); c.add_argument("--kind", type=int, default=2)
    a = ap.parse_args()
    if a.cmd == "cold":
        from pm import PM, TOS
        h = PM(disk=Path(a.disk).resolve(), memsize_kb=a.mem, machine=a.machine, tos=TOS[a.tos])
        try:
            t0 = time.time()
            h.boot_to_game()
            print(f"boot {time.time() - t0:.0f} s; marker {h.debug('m $b87f8 4', 0.5).splitlines()[-1] if False else ''}", flush=True)
            if a.mhz:
                h.set_cpuclock(a.mhz)
            time.sleep(2)
            pokes = ["w $4bb42 $%02x $%02x" % (a.kind >> 8, a.kind & 255), "w $4bb44 $20 $00"]
            from pmtick import at_flip
            at_flip(h, pokes)
            time.sleep(1.0)
            print("RESULT fps with rain on:", h.fps(1000), flush=True)
            got = dump_frames(h, [], [], a.nframes, a.machine == "tt", 8)
            shot = h.shot(str(Path(a.outdir) / "hatari_screenshot.png")) if Path(a.outdir).exists() or Path(a.outdir).mkdir(parents=True) is None else None
        finally:
            h.close()
        rows, imgs = analyse(got, a.kind, Path(a.outdir), "cold", a.machine == "tt")
        print("frame tick kind(at dump) left base matchfrac d3")
        for r in rows:
            print(*r)
        nr = sum(1 for r in rows if r[5] >= 0.98)
        print(f"RESULT cold {a.machine} TOS {a.tos} {a.mem} KB {a.mhz} MHz: rain on {nr} of {len(rows)} consecutive frames")
        montage(imgs, str(Path(a.outdir) / f"strip_cold_{a.machine}_{Path(a.disk).stem}.png"))
        return
    os.environ["PM_WX"] = a.wx
    import pmtick
    from pm import PM, SNAP
    live = pmtick.build_live(pmtick.NAMES, f"build/tick/rain_{a.wx}")
    h = PM(snapshot=str(SNAP / f"{a.snap}.sav"))
    try:
        time.sleep(1.5)
        pokes = a.poke + ([] if a.kind < 0 else ["w $4bb42 $%02x $%02x" % (a.kind >> 8, a.kind & 255), "w $4bb44 $%02x $%02x" % (a.left >> 8, a.left & 255)])
        got = dump_frames(h, ["e VBL"] if a.orig else pmtick.apply_cmds(live), pokes, a.nframes, False, a.mhz)
    finally:
        h.close()
    rows, imgs = analyse(got, a.kind, Path(a.outdir), a.wx)
    print("frame tick kind(at dump) left base matchfrac d3")
    for r in rows:
        print(*r)
    nr = sum(1 for r in rows if r[5] >= 0.98)
    kn = [r for r in rows if r[2] in (1, 2)]
    print(f"RESULT {a.snap} {a.mhz} MHz {'orig' if a.orig else a.wx}: rain on {nr} of {len(rows)} consecutive frames; "
          f"{sum(1 for r in kn if r[5] >= 0.98)} of the {len(kn)} frames dumped while the rain clock was on")
    montage(imgs, str(Path(a.outdir) / f"strip_{a.snap}_{a.mhz}_{'orig' if a.orig else a.wx}.png"))


if __name__ == "__main__":
    main()
