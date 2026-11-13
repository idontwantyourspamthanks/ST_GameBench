"""PopTTPtr gate cell (test scaffolding): one cold boot (TT or Falcon floppy), every screen of the user's route, pointer-visibility statistics.

    full_cell(label, cell, floppy_image, route)   route = 'new' (NEW GAME + typed world name) | 'start' (START GAME)
Per phase: the VBL sampler (frames, frames whose displayed buffer holds the last pointer draw, flips) and, in play, the pixel check of the dumped
buffers (the pointer sprite searched in the displayed buffer and in the other one at the entry of the VBL routine) at four screen areas, still and moving.
Everything is raw in <label>.json plus the Hatari log excerpts of the sampler (not kept).
"""
import json, threading, time, re, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ttp
from ttp import pc, SH, GP

POS = dict(book=(100, 100), panel=(150, 340), right=(590, 330), minimap=(70, 50))
GLOBE = (608, 352)


def phase(h, D, name, out, secs=3, move=False):
    st, _ = ttp.measure(h, D, secs=secs, move=move, name="ph")
    out["phases"][name] = st
    print(f"  [{out['label']}] {name}: {st}", flush=True)
    return st


def pixel_check(h, cell, D, n=6):
    res = {}
    for name, (x, y) in POS.items():
        pc.goto_shot(h, cell, "game", x, y)
        time.sleep(1.0)
        r = ttp.sample_dump(h, D, n=n, label="pc" + name)
        res[name] = dict(n=len(r), shown1=sum(len(e["shown"]) == 1 for e in r), shown0=sum(len(e["shown"]) == 0 for e in r), shown2=sum(len(e["shown"]) >= 2 for e in r),
                         other0=sum(len(e["other"]) == 0 for e in r), f12zero=sum(e["f12"] == 0 for e in r), pos=sorted({(e["x"], e["y"]) for e in r}))
    return res


def moving_check(h, cell, D, n=14, start=(90, 330), amp=30):
    stop = [False]

    def mover():
        k = 0
        while not stop[0]:
            try:
                h.rel(amp if (k // 3) % 2 == 0 else -amp, 0, 3)
            except Exception:
                pass
            k += 1
    pc.goto_shot(h, cell, "game", *start)
    time.sleep(0.5)
    th = threading.Thread(target=mover)
    th.start()
    try:
        r = ttp.sample_dump(h, D, n=n, label="mv")
    finally:
        stop[0] = True
        th.join()
    return dict(n=len(r), shown1=sum(len(e["shown"]) == 1 for e in r), shown0=sum(len(e["shown"]) == 0 for e in r), shown2=sum(len(e["shown"]) >= 2 for e in r),
                other0=sum(len(e["other"]) == 0 for e in r), f12zero=sum(e["f12"] == 0 for e in r), distinct_positions=len({(e["x"], e["y"]) for e in r}))


def full_cell(label, cell, path, route, play_secs=6, endworld=True, mem=None):
    out = dict(label=label, cell=cell, image=str(path), route=route, phases={})
    h, tm = ttp.boot(cell, path, mem=mem)
    out["t_menu"] = tm
    try:
        if tm is None:
            out["error"] = "menu not reached"
            return out
        pc.goto_shot(h, cell, "menu", *pc.CONQUEST)
        h.click(hold=0.4)
        sref = pc.REF / ("tt_start_page.png" if cell == "tt" else "falcon_start_page.png")
        (gx, gy), _ = pc.GEOM[(cell, "game")]
        sbox = (60 + gx, 105 + gy, 340 + gx, 225 + gy)
        if pc.wait_for_crop(h, sref, sbox, 180) is None:
            out["error"] = "start page not reached"
            return out
        time.sleep(2)
        D = pc.delta(h)
        out["D"] = D
        if D is None:
            out["error"] = "no payload"
            return out
        phase(h, D, "world page (pointer over START/NEW buttons)", out)
        ttp.shot(h, f"{label}_p1_worldpage.png")
        if route == "new":
            pc.goto_shot(h, cell, "game", *ttp.NEWGAME_XY)
            h.click(hold=0.4)
            time.sleep(3)
            phase(h, D, "name entry (empty field)", out)
            ttp.shot(h, f"{label}_p2_nameentry.png")
            for c in "genesis":
                h.key(c, 0.35)
                time.sleep(0.6)
            phase(h, D, "name entry (typed)", out, secs=2)
            h.keypress(28)
            time.sleep(4)
            phase(h, D, "world page after the name", out, secs=2)
            ttp.shot(h, f"{label}_p3_afterreturn.png")
        pc.goto_shot(h, cell, "game", *ttp.START_XY)
        h.click(hold=0.4)
        time.sleep(12)
        out["turn"] = [h.peekw(0x3C506 + D)]
        phase(h, D, "play, pointer in the left panel, still", out, secs=play_secs)
        ttp.shot(h, f"{label}_p4_play_still.png")
        phase(h, D, "play, pointer in the left panel, moving", out, secs=play_secs, move=True)
        ttp.shot(h, f"{label}_p5_play_moving.png")
        out["pixel_still"] = pixel_check(h, cell, D)
        print("  pixel still", out["pixel_still"], flush=True)
        out["pixel_moving"] = moving_check(h, cell, D)
        print("  pixel moving", out["pixel_moving"], flush=True)
        # the pointer over the map (the game draws its own cross there; the VBL pointer is hidden by the hover code)
        pc.goto_shot(h, cell, "game", 300, 250)
        time.sleep(1)
        phase(h, D, "play, pointer over the map", out, secs=2)
        ttp.shot(h, f"{label}_p6_map.png")
        # dialog: GAME SETUP (globe)
        pc.goto_shot(h, cell, "game", *GLOBE)
        h.click(hold=0.4)
        time.sleep(2.5)
        phase(h, D, "GAME SETUP dialog", out, secs=2)
        ttp.shot(h, f"{label}_p7_setup.png")
        out["pixel_dialog"] = ttp.sample_dump(h, D, n=4, label="dlg")
        out["pixel_dialog"] = [dict(shown=e["shown"], other=e["other"], f12=e["f12"]) for e in out["pixel_dialog"]]
        h.keypress(1)
        time.sleep(1.5)
        if endworld:
            # end of the world: fast-forward until the turn counter stops (GAME LOST / WON dialog)
            h.cmd("hatari-option --fast-forward on")
            last = None
            t0 = time.time()
            while time.time() - t0 < 420:
                time.sleep(3)
                try:
                    t_ = h.peekw(0x3C506 + D)
                except Exception:
                    continue
                if t_ == last and t_:
                    break
                last = t_
            h.cmd("hatari-option --fast-forward off")
            time.sleep(1)
            out["end_turn"] = last
            phase(h, D, "end of world dialog", out, secs=3)
            ttp.shot(h, f"{label}_p8_endworld.png")
            out["pixel_end"] = [dict(shown=e["shown"], other=e["other"], f12=e["f12"]) for e in ttp.sample_dump(h, D, n=4, label="end")]
        lg = h._logtext()
        out["errors"] = [l[:120] for l in lg.splitlines() if re.search("Bus Error|Address Error|double bus|CPU halted", l)]
        return out
    finally:
        try:
            Path(GP / f"work/gates/ttptr_{label}.json").write_text(json.dumps(out, indent=1, default=str))
        finally:
            h.close()


def shots_run(label, cell, path, n=26, dt=0.8, still_xy=(100, 100)):
    """NEW GAME route to play; then n screenshots with the pointer still (book area), n with the pointer moving (left panel / book); PNGs in work/shots/ttptr/<label>/."""
    d = SH / label
    d.mkdir(exist_ok=True)
    h, tm = ttp.boot(cell, path)
    out = dict(label=label, t_menu=tm, still=[], moving=[])
    try:
        pc.goto_shot(h, cell, "menu", *pc.CONQUEST)
        h.click(hold=0.4)
        sref = pc.REF / ("tt_start_page.png" if cell == "tt" else "falcon_start_page.png")
        (gx, gy), _ = pc.GEOM[(cell, "game")]
        if pc.wait_for_crop(h, sref, (60 + gx, 105 + gy, 340 + gx, 225 + gy), 180) is None:
            raise RuntimeError("start page not reached")
        time.sleep(2)
        D = pc.delta(h)
        pc.goto_shot(h, cell, "game", *ttp.NEWGAME_XY)
        h.click(hold=0.4)
        time.sleep(3)
        for c in "genesis":
            h.key(c, 0.35)
            time.sleep(0.6)
        h.keypress(28)
        time.sleep(4)
        pc.goto_shot(h, cell, "game", *ttp.START_XY)
        h.click(hold=0.4)
        time.sleep(12)
        pc.goto_shot(h, cell, "game", *still_xy)
        time.sleep(1.0)
        out["pointer_vars"] = ttp.rdmem(h, 0x24786 + D, 4).hex()
        out["D"] = D
        t0 = time.time()
        for i in range(n):
            f = ttp.shot(h, f"{label}/still_{i:02d}.png")
            out["still"].append(f)
            time.sleep(dt)
        out["still_secs"] = round(time.time() - t0, 1)
        stop = [False]

        def mover():
            k = 0
            while not stop[0]:
                try:
                    h.rel(25 if (k // 3) % 2 == 0 else -25, 0, 3)
                except Exception:
                    pass
                k += 1
        pc.goto_shot(h, cell, "game", 90, 330)
        th = threading.Thread(target=mover)
        th.start()
        t0 = time.time()
        try:
            for i in range(n):
                f = ttp.shot(h, f"{label}/moving_{i:02d}.png")
                out["moving"].append(f)
                time.sleep(dt)
        finally:
            stop[0] = True
            th.join()
        out["moving_secs"] = round(time.time() - t0, 1)
        return out
    finally:
        Path(GP / f"work/gates/ttptr_shots_{label}.json").write_text(json.dumps(out, indent=1, default=str))
        h.close()
