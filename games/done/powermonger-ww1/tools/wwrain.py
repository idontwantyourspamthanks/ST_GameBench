#!/usr/bin/env python3
"""Rain-per-frame gate for tick_rain (port of master's tools/pmrain.py `cold`; notes: work/notes/RESULTS_stage04.md).

    python3 tools/wwrain.py cold --disk build/default/floppy.st --nframes 40 --mhz 16 --workdir DIR [--kind 2] [--tag NAME]

Cold boot of a BUILT floppy (noprot set: straight to the map view), rain forced on at a flip (`$50fdc` = kind, `$50fde` = ticks left), then every
main-loop top (`b pc=$13d58`) dumps RAM $0-$7ffff + the video registers + the palette.  A frame HAS rain iff, for one of the 64 row-aligned phases of
the game's own table ($1b604 kind 1 colour 15, $1b728 kind 2 colour 5; the draw routine $1b5b6 ORs table row (phase - 4 per scanline)), every pixel of
the predicted mask in the 3D window (rows 13..165, x >= 80) carries the rain colour.  Frames without rain score 0.02-0.09, with rain 1.000.
Prints `RAIN <tag>: rain on N of M consecutive frames` and `GATE rain <tag> ... PASS|FAIL`.  The comparison build (tick_wx instead of tick_rain)
must show FEWER frames with rain at 16 MHz (render-only passes), tick_rain all of them.
"""
from __future__ import annotations
import argparse
import sys
import threading
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pmww  # noqa: E402
import wwtick  # noqa: E402
from PIL import Image  # noqa: E402

LOOPTOP = 0x13D58
KIND, LEFT, TICK = 0x50FDC, 0x50FDE, 0x2ED90
TAB = {1: 0x1B604, 2: 0x1B728}
LEN = 0x80000


def decode(buf: bytes) -> np.ndarray:
    w = np.frombuffer(buf, dtype=">u2").reshape(200, 20, 4)
    bits = ((w[:, :, None, :] >> (15 - np.arange(16))[None, None, :, None]) & 1)
    return (bits[..., 0] | bits[..., 1] << 1 | bits[..., 2] << 2 | bits[..., 3] << 3).reshape(200, 320)


def palette(raw: bytes) -> np.ndarray:
    v = np.frombuffer(raw[:32], dtype=">u2").astype(int)
    f = lambda n: (((n & 7) << 1) | ((n >> 3) & 1)) * 17
    return np.stack([f(v >> 8), f(v >> 4), f(v)], 1).astype(np.uint8)


def mask_of(ram: bytes, kind: int, d3_0: int) -> np.ndarray:
    base = TAB[kind]
    d3 = (d3_0 - 4 * np.arange(194)) & 255
    L = np.array([int.from_bytes(ram[base + x: base + x + 4], "big") for x in d3], dtype=np.uint64)
    wlo, whi = (L & 0xFFFF).astype(np.uint16), (L >> 16).astype(np.uint16)
    words = np.stack([wlo if g % 2 == 0 else whi for g in range(16)], 1)
    bits = (words[:, :, None] >> (15 - np.arange(16))[None, None, :]) & 1
    m = np.zeros((194, 320), bool)
    m[:, 64:] = bits.reshape(194, 256).astype(bool)
    return m


def has_rain(ram: bytes, idx: np.ndarray, kind: int):
    rc = 15 if kind == 1 else 5
    sub = idx[6:200]
    win = np.zeros((194, 320), bool)
    win[13 - 6:166 - 6, 80:] = True
    best = (0.0, -1)
    for d3 in range(0, 256, 4):
        mm = mask_of(ram, kind, d3) & win
        n = int(mm.sum())
        f = float((sub[mm] == rc).sum()) / n if n else 0.0
        if f > best[0]:
            best = (f, d3)
    return best


def dump_frames(h, nframes):
    cur, vid, pal = h.R / "rcur.bin", h.R / "rvid.bin", h.R / "rpal.bin"
    f = h.R / "rdump.txt"
    f.write_text(f"savebin {vid} $ff8200 $10\nsavebin {pal} $ff8240 $20\nsavebin {cur} $0 ${LEN:x}\n")
    for p in (cur, vid, pal):
        p.unlink(missing_ok=True)
    got, stop = [], threading.Event()

    def poll():
        last = None
        while not stop.is_set():
            try:
                st = cur.stat()
            except FileNotFoundError:
                time.sleep(0.003)
                continue
            if st.st_size == LEN and st.st_mtime_ns != last:
                time.sleep(0.03)
                st2 = cur.stat()
                if st2.st_mtime_ns == st.st_mtime_ns and st2.st_size == LEN:
                    last = st.st_mtime_ns
                    got.append((cur.read_bytes(), vid.read_bytes(), pal.read_bytes()))
            time.sleep(0.004)
    th = threading.Thread(target=poll, daemon=True)
    th.start()
    h.debug("b all", 0.3)
    h.cmd(f"hatari-debug b pc = ${LOOPTOP:x} :trace :file {f}")
    t0 = time.time()
    while len(got) < nframes and time.time() - t0 < 900:
        time.sleep(0.2)
    h.debug("b all", 0.3)
    time.sleep(0.5)
    stop.set()
    th.join()
    return got


def cmd_cold(a):
    kind = a.kind
    h = pmww.PMW(disk=Path(a.disk), workdir=a.workdir, machine="ste", tos=pmww.TOS["1.62"], memsize_kb=1024)
    try:
        h.boot_to_map(noprot=True, swap=False, log=lambda s: print("  " + s, flush=True))
        if a.mhz != 8:
            h.set_cpuclock(a.mhz)
        time.sleep(2)
        wwtick.at_flip(h, [f"w ${KIND:x} $00 ${kind:02x}", f"w ${LEFT:x} $20 $00"])
        time.sleep(1.0)
        got = dump_frames(h, a.nframes)
        Path(a.workdir, "shots").mkdir(exist_ok=True)
    finally:
        h.close()
    rows, imgs = [], []
    for i, (ram, vid, pal) in enumerate(got):
        base = (vid[1] << 16) | (vid[3] << 8) | vid[0xD]
        base = base if base < 0x80000 else int.from_bytes(ram[0x2ED98:0x2ED9C], "big")
        idx = decode(ram[base:base + 32000])
        imgs.append(palette(pal)[idx])
        tick = int.from_bytes(ram[TICK:TICK + 4], "big")
        k = int.from_bytes(ram[KIND:KIND + 2], "big")
        left = int.from_bytes(ram[LEFT:LEFT + 2], "big", signed=True)
        f, d3 = has_rain(ram, idx, k if k in (1, 2) else kind)
        rows.append((i, tick, k, left, hex(base), round(f, 3), d3))
    print("frame tick kind left base matchfrac phase")
    for r in rows:
        print(*r)
    nr = sum(1 for r in rows if r[5] >= 0.98)
    kn = [r for r in rows if r[2] in (1, 2)]
    ticks = len({r[1] for r in rows})
    tag = a.tag or Path(a.disk).parent.name
    print(f"RAIN {tag} {a.mhz} MHz: rain on {nr} of {len(rows)} consecutive frames; {sum(1 for r in kn if r[5] >= 0.98)} of the {len(kn)} frames dumped while the rain clock was on; "
          f"{ticks} distinct world ticks in the window", flush=True)
    x0, y0, x1, y1 = 80, 6, 320, 166
    cols, w, hh = 4, x1 - x0, y1 - y0
    M = Image.new("RGB", (cols * (w + 2), ((len(imgs) + cols - 1) // cols) * (hh + 2)), (255, 0, 255))
    for i, im in enumerate(imgs):
        M.paste(Image.fromarray(im[y0:y1, x0:x1]), ((i % cols) * (w + 2), (i // cols) * (hh + 2)))
    M.save(Path(a.workdir) / "shots" / f"strip_{tag}_{a.mhz}.png")
    if a.expect == "all":
        ok = nr >= len(kn) - 1 and len(kn) >= a.nframes - 2          # the frame rendered before the clock was switched on has none
        print(f"GATE rain {tag} {a.mhz} MHz rain on every frame {'PASS' if ok else 'FAIL'} {nr} of {len(rows)} (clock on in {len(kn)})")
    else:
        ok = nr < len(kn) - 1
        print(f"GATE rain {tag} {a.mhz} MHz (control build) rain on only some frames {'PASS' if ok else 'FAIL'} {nr} of {len(rows)}")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("cold")
    c.add_argument("--disk", required=True)
    c.add_argument("--nframes", type=int, default=40)
    c.add_argument("--mhz", type=int, default=16)
    c.add_argument("--kind", type=int, default=2)
    c.add_argument("--workdir", required=True)
    c.add_argument("--tag")
    c.add_argument("--expect", choices=["all", "some"], default="all")
    a = ap.parse_args()
    return cmd_cold(a)


if __name__ == "__main__":
    sys.exit(main())
