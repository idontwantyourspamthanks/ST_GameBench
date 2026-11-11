#!/usr/bin/env python3
"""One cell of the combined-default-set cold-boot gate (work/notes/combined.md): the release set = p7 triple buffering + qol keys / hover +
tt_ptr + the rest, on one machine.

    python3 tools/pmcombined.py --disk build/comb/floppy/powermonger.st --machine ste --tos 1.62 --mem 1024
    python3 tools/pmcombined.py --hd build/comb/hd --acsi --saveload --machine ste --tos 1.62 --mem 1024
    python3 tools/pmcombined.py --disk ... --machine tt --tos 3.06 --mem 4096 --hopts "--cpuclock 32 --monitor vga"
    python3 tools/pmcombined.py --disk ... --machine falcon --tos 4.04 --mem 4096 --hopts "--borders false"

Cold boot (pm.boot_to_game) -> map view, then: the patch sites in RAM, marker PMPO, `LIVE` ($baaf0, tt_ptr), the three buffers (L, D)
at every flip, the pointer in the SHOWN picture in N screenshots, the key F (Get Food: $57fd4 = 6, toggled off again by F), a village hover
(a house sprite found through the sprite routine $12138, pointer rested on it: HIT, text, tooltip pixels), fps and world ticks / s of the map
view and of get_men (pmreg.measure), the three-buffer sample again after get_men, optionally the game's own save + load.
Every measurement prints one `RESULT ...` line; the `CELL` lines summarise.
"""
from __future__ import annotations

import argparse
import shlex
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent.parent.parent.parent / "tools"), str(HERE)]
import pmab as AB  # noqa: E402
import pmpatch  # noqa: E402
import pmreg  # noqa: E402
import pmtick  # noqa: E402
import pmtriple as PT  # noqa: E402
from pm import TOS  # noqa: E402

SITES = {"p7_wait": (0x13090, "4eb9000db200"), "p7_flip": (0x1386C, "4eb9000db100"), "p7_tail": (0x1898, "4eb9000db3004e71"),
         "tt_ptr": (0x188C, "4eb9000ba940"), "qol_hover": (0x130B6, "4eb9000cfa80"), "qol_hover2": (0x12138, "4eb9000cd560"),
         "qol_keys": (0x130FC, "4eb9000cf830"), "qol_keys2": (0x199C, "4eb9000cd610")}
LIVE = 0xBAAF0
GAME_OX_OY = {832: (96, 58), 640: (0, 0), 648: (2, 64)}      # screenshot width -> picture origin (as pmreg.tooltip)


def shot_img(h):
    from PIL import Image
    im = Image.open(h.shot()).convert("RGB")
    return im, GAME_OX_OY.get(im.width, (96, 58))


def crop_st(im, org, x0, y0, x1, y1):
    return im.crop((org[0] + 2 * x0, org[1] + 2 * y0, org[0] + 2 * x1, org[1] + 2 * y1))


def ndiff(a, b, thr=40):
    from PIL import ImageChops
    return sum(1 for p in ImageChops.difference(a, b).convert("L").getdata() if p > thr)


def pointer_frames(h, n=20, spot=(20, 118)):
    """The software pointer in the SHOWN picture: a 16 x 16 ST-pixel crop at `spot` of the (static) left panel with the pointer parked away
    (the reference) against n screenshots with the pointer on `spot`.  Reports how many of the n show it (>= 20 changed pixels)."""
    h.goto_st(30, 30)
    time.sleep(1.5)
    ref, org = shot_img(h)
    box = (spot[0], spot[1], spot[0] + 16, spot[1] + 16)
    ref_c = crop_st(ref, org, *box)
    ref_hits = []
    h.goto_st(*spot)
    time.sleep(1.0)
    hits, counts = 0, []
    for _ in range(n):
        im, org = shot_img(h)
        c = ndiff(ref_c, crop_st(im, org, *box))
        counts.append(c)
        hits += c >= 20
        time.sleep(0.15)
    mp = h.mpos()
    print(f"RESULT pointer: pointer words {mp} after moving to {spot}; {hits} of {n} screenshots show the pointer (changed pixels in the 16x16 crop: min {min(counts)} "
          f"median {sorted(counts)[len(counts) // 2]} max {max(counts)})", flush=True)
    return hits, n


def find_house(h, secs=4.0):
    """Screen positions (d0, d1) of house sprites: every call of the sprite routine $12138 whose object a3 lies in the house table $4f916..$51536."""
    f = h.R / "house.txt"
    f.write_text("e d0\ne d1\ne a3\n")
    h.debug("b all", 0.3)
    s0 = len(h._logtext())
    h.cmd(f"hatari-debug b pc = $12138 && a3 > $4f915 && a3 < $51536 :trace :file {f}")
    time.sleep(secs)
    h.debug("b all", 0.5)
    seen = {}
    for blk in h._logtext()[s0:].split("CPU breakpoint condition(s) matched")[1:]:
        m = [int(v) for v in AB.NUM.findall(blk)]
        if len(m) >= 3:
            seen[(m[0] & 0xFFFF, m[1] & 0xFFFF, m[2])] = seen.get((m[0] & 0xFFFF, m[1] & 0xFFFF, m[2]), 0) + 1
    return seen


def hover_test(h, shots):
    cands = []
    for rnd in range(8):
        seen = find_house(h)
        cands = [(x, y, a) for (x, y, a), _ in sorted(seen.items()) if 70 <= x <= 300 and 12 <= y <= 140]
        print(f"RESULT hover: round {rnd}: house sprite calls seen: {len(seen)} distinct (d0, d1, a3): {sorted(seen)[:8]}; in the window {len(cands)}", flush=True)
        if cands:
            break
        for k in ("Right", "Down", "Left", "Up"):        # scroll the view (the game's own cursor keys) to look for a village
            for _ in range(3):
                h.key(k, hold=0.4)
                time.sleep(0.8)
    if not cands:
        print("RESULT hover: NO house in the window", flush=True)
        return False
    ok = False
    from PIL import Image  # noqa: F401
    h.goto_st(150, 100)
    time.sleep(1.5)
    away, org = shot_img(h)
    box = (112, 0, 320, 6)
    away_c = crop_st(away, org, *box)
    for x, y, a in cands[:4]:
        for dx, dy in ((4, 4), (6, 6), (2, 2)):
            h.goto_st(x + dx, y + dy)
            time.sleep(3.0)
            hit, txt = h.peekl(0xCD5E2), h.peekw(0xCDC12)
            if hit:
                im, org = shot_img(h)
                n = ndiff(away_c, crop_st(im, org, *box))
                im.save(shots / f"hover_{h.R.name}.png") if shots else None
                print(f"RESULT hover: sprite ({x},{y}) obj ${a:x}, pointer on ({x + dx},{y + dy}) = {h.mpos()}: HIT ${hit:x}, text flag {txt}, "
                      f"tooltip box pixels changed vs pointer away {n}", flush=True)
                ok = n > 100 and txt == 1
                return ok
    print(f"RESULT hover: HIT stayed 0 on {cands[:4]} (pointer {h.mpos()}, text flag {h.peekw(0xCDC12)})", flush=True)
    return False


def ptr_buffer(h, secs=6.0):
    """Where is the pointer right after a flip?  At every return of the main loop's flip ($13872) read the pointer's saved-screen address
    [$1c49a] and the buffer about to be scanned [$2df78]: on a TT with tt_ptr the pointer is drawn into the new displayed buffer INSIDE the flip
    ([$1c49a] within [L, L+32000)); on an ST / STE it is drawn by the next VBL handler (the record still points into the previous frame)."""
    f = h.R / "ptrbuf.txt"
    f.write_text("e ($1c49a).l\ne ($2df78).l\ne ($ff8201).b\n")
    h.debug("b all", 0.3)
    s0 = len(h._logtext())
    h.cmd(f"hatari-debug b pc = $13872 :trace :file {f}")
    time.sleep(secs)
    h.debug("b all", 0.5)
    n = inside = 0
    for blk in h._logtext()[s0:].split("CPU breakpoint condition(s) matched")[1:]:
        m = [int(v) for v in AB.NUM.findall(blk)]
        if len(m) >= 3:
            n += 1
            inside += m[1] <= m[0] < m[1] + 32000
    print(f"RESULT pointer buffer: at {n} flip returns the pointer record [$1c49a] lies inside the new displayed buffer [$2df78] in {inside} (hidden pointer: not drawn)", flush=True)
    return n, inside


def key_f(h):
    """Real key F (xdotool) -> Get Food ($57fd4 = 6, same as the icon click), F again -> off."""
    before = h.peekw(0x57FD4)
    h.key("f", hold=0.05)
    got = 0
    for _ in range(40):
        time.sleep(0.25)
        got = h.peekw(0x57FD4)
        if got == 6:
            break
    h.key("f", hold=0.05)
    off = None
    for _ in range(40):
        time.sleep(0.25)
        off = h.peekw(0x57FD4)
        if off != 6:
            break
    print(f"RESULT key F: $57fd4 {before} -> {got} (Get Food = 6) -> {off} after the second F", flush=True)
    return got == 6


def triple(h, tag, secs=6.0):
    s = PT.sample_lds(h, secs)
    bufs = set()
    for k in s:
        bufs.update(k.strip("()").split(","))
    c = h.ram(PT.BUFC, 32000)
    print(f"RESULT triple {tag}: (L, D) at flip entry {s}; buffers used {sorted(bufs)}; C $70000 non-zero {sum(1 for b in c if b)} B; "
          f"IN/OURS {h.peekw(0xDB000)}/{h.peekw(0xDB002)}", flush=True)
    return len(bufs) == 3


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--disk")
    ap.add_argument("--hd")
    ap.add_argument("--acsi", action="store_true")
    ap.add_argument("--machine", default="ste")
    ap.add_argument("--tos", default="1.62")
    ap.add_argument("--mem", type=int, default=1024)
    ap.add_argument("--mhz", type=int, nargs="*", default=[])
    ap.add_argument("--vbls", type=int, default=1000)
    ap.add_argument("--saveload", action="store_true")
    ap.add_argument("--shots")
    ap.add_argument("--hopts", default="")
    ap.add_argument("--no-fps", action="store_true")
    a = ap.parse_args()
    name = f"{'HD' + ('-acsi' if a.acsi else '-gemdos') if a.hd else 'floppy'} {a.machine} TOS {a.tos} {a.mem} KB"
    print(f"CELL {name}", flush=True)
    shots = Path(a.shots) if a.shots else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    h, ok, res = None, True, {}
    try:
        h = pmpatch.make_pm(Path(a.disk).resolve() if a.disk else None, Path(a.hd).resolve() if a.hd else None, acsi=a.acsi,
                            machine=a.machine, tos=TOS[a.tos], memsize_kb=a.mem, extra=shlex.split(a.hopts))
        t0 = time.time()
        h.boot_to_game()
        marker = h.peekl(pmpatch.MARKER).to_bytes(4, "big")
        flags = h.peekl(pmpatch.FLAGS)
        print(f"RESULT boot: {time.time() - t0:.0f} s, in_game {h.in_game()}, MARKER {marker!r} FLAGS {flags:#x}, sync ${pmreg.rdb(h, 0xFF820A):02x}, "
              f"tt_ptr LIVE ${pmreg.rdb(h, LIVE):02x}", flush=True)
        ok &= marker == b"PMPO"
        bad = {n: (h.ram(s, len(w) // 2).hex(), w) for n, (s, w) in SITES.items() if h.ram(s, len(w) // 2).hex() != w}
        print(f"RESULT sites: {len(SITES) - len(bad)} of {len(SITES)} live" + (f"; WRONG {bad}" if bad else ""), flush=True)
        ok &= not bad
        if shots:
            h.shot(str(shots / f"{a.machine}_{a.tos}_{a.mem}_{'hd' if a.hd else 'fl'}_map.png"))
        n_ptr, n = pointer_frames(h)
        res["pointer"] = f"{n_ptr}/{n}"
        ok &= n_ptr >= n * 0.9
        res["ptrbuf"] = ptr_buffer(h)
        res["F"] = key_f(h)
        ok &= res["F"]
        res["hover"] = hover_test(h, shots)
        ok &= res["hover"]
        res["triple_map"] = triple(h, "map view")
        ok &= res["triple_map"]
        if not a.no_fps:
            clocks = a.mhz or [0]
            for mhz in clocks:
                if mhz:
                    h.set_cpuclock(mhz)
                    time.sleep(2)
                res[f"map{mhz}"] = pmreg.measure(h, f"map view{f' {mhz} MHz' if mhz else ''}", a.vbls, True)
            print(f"RESULT get_men: {h.scenario_get_men()} people moving", flush=True)
            for mhz in clocks:
                if mhz:
                    h.set_cpuclock(mhz)
                    time.sleep(2)
                res[f"get_men{mhz}"] = pmreg.measure(h, f"get_men{f' {mhz} MHz' if mhz else ''}", a.vbls, True)
            res["triple_gm"] = triple(h, "after get_men")
            ok &= res["triple_gm"]
        print(f"RESULT after: in_game {h.in_game()} MARKER {h.peekl(pmpatch.MARKER).to_bytes(4, 'big')!r}", flush=True)
        if a.saveload:
            sl = pmpatch.run_saveload(h, a.acsi)
            ok &= bool(sl)
            time.sleep(3)
            print(f"RESULT saveload: {sl}; after: in_game {h.in_game()} iter {h.iter_count()}", flush=True)
            res["triple_sl"] = triple(h, "after save + load")
            ok &= res["triple_sl"]
        if shots:
            h.shot(str(shots / f"{a.machine}_{a.tos}_{a.mem}_{'hd' if a.hd else 'fl'}_end.png"))
        print(f"CELL DONE {name}: {'OK' if ok else 'CHECK'} {res}", flush=True)
        return 0 if ok else 2
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        print(f"CELL FAILED {name}: {e!r}", flush=True)
        if h is not None:
            try:
                print(f"  MARKER={h.peekl(pmpatch.MARKER).to_bytes(4, 'big')!r} FLAGS={h.peekl(pmpatch.FLAGS):#x}", flush=True)
                d = shots or Path("/tmp")
                d.mkdir(parents=True, exist_ok=True)
                h.shot(str(d / f"fail_{a.machine}_{a.tos}_{a.mem}.png"))
            except Exception:  # noqa: BLE001
                pass
        return 1
    finally:
        if h is not None:
            h.close()


if __name__ == "__main__":
    sys.exit(main())
