#!/usr/bin/env python3
"""Load times (in emulated VBLs), resource-cache trace, long regression sequence and free-RAM pattern proof of one build on one machine
(work/notes/release.md).  A cell = cold boot -> map view -> a sequence of Retire variants, each followed by the next conquest.

    python3 tools/pmload.py --disk build/rel/cap/floppy/powermonger.st --manifest build/rel/cap/floppy.json --machine ste --tos 1.62 --mem 1024 --seq lose,win,lose
    python3 tools/pmload.py --hd build/rel/cap/hd --acsi --manifest build/rel/cap/hd.json --seq none ...        # none = boot to the map view only
    ... --fill      free spans of $B8800..$EFFFF (manifest) get a pattern at the hand-over; checked after every stage
    ... --seq win,final   `final` = the last island's ending pictures (the cell ends there)

Times are VBL counts read through the debugger (`e VBL`) at the click and at the moment the next screen is seen (one screenshot poll of
0.7 s wall later), so every figure carries a constant poll bias; it cancels when two builds are compared.  Every disk load of the game's
resource loader ($df96) and every cache skip of pm_cachecap ($dc114) is logged with the VBL and printed at the end.
"""
from __future__ import annotations

import argparse
import re
import shlex
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent.parent.parent.parent / "tools"), str(HERE)]
import pm  # noqa: E402
import pmpatch  # noqa: E402
import pmretire as PR  # noqa: E402
from pm import TOS  # noqa: E402

E040, E084 = 0xE040, 0xE084
NRES = 16


def vbl(h) -> int:
    return int(re.findall(r"#(\d+) \(dec\)", h.debug("e VBL", 0.25))[-1])


TRACE_BPS = (("call", 0xDF5A, "e VBL\nr\n"),       # $df5a: the loader was called, d2.w = resource number
             ("miss", 0xDF96, "e VBL\n"),           # not cached: the resource comes from the disk / the file system
             ("ret", 0xE03C, "e VBL\n"),            # the loader returns (every path)
             ("skip", 0xDC114, "e VBL\nr\n"))      # pm_cachecap: this resource does not fit below $b8000, not cached (d2 = its size)


def arm_trace(h):
    for kind, addr, script in TRACE_BPS:
        (h.R / f"tr_{kind}.txt").write_text(script)
        h.cmd(f"hatari-debug b pc = ${addr:x} :trace :file {h.R / f'tr_{kind}.txt'}")
    time.sleep(0.5)


def trace_events(h):
    """[(vbl, kind, d2 or None)] in log order."""
    txt = h._logtext()
    out = []
    for m in re.finditer(r"Reading debugger commands from '[^']*/tr_(\w+)\.txt'\.\.\.\n(?:Changed[^\n]*\n)?> e VBL\n= [^\n]*#(\d+) \(dec\)[^\n]*\n(?:> r\n(.*?)(?=\nChanged back|\Z))?", txt, re.S):
        kind, v, regs = m.group(1), int(m.group(2)), m.group(3) or ""
        d2 = re.search(r"D2\s+([0-9A-Fa-f]{8})", regs)
        out.append((v, kind, int(d2.group(1), 16) if d2 else None))
    return out


def loader_summary(run, ev):
    """For every timed step: the loader calls inside it and the VBL at which the last one returned (relative to the click)."""
    print("LOADER per step (res: n = from the disk, c = from the cache; skip = pm_cachecap kept it out of the cache):", flush=True)
    for label, v0, v1 in run.ev:
        calls = []
        for v, k, d2 in ev:
            if v0 - 3 <= v <= v1 + 3:
                calls.append((v, k, d2))
        res, last_ret, pending = [], None, None
        for v, k, d2 in calls:
            if k == "call":
                pending = [v, d2 & 0xFFFF, "c"]
                res.append(pending)
            elif k == "miss" and pending:
                pending[2] = "n"
            elif k == "skip" and pending:
                pending[2] = "n+skip"
            elif k == "ret":
                last_ret = v
        txt = " ".join(f"{r}:{c}" for _, r, c in res) or "-"
        print(f"  {label}: {v1 - v0} VBL by poll; loader calls [{txt}]; "
              + (f"last loader return {last_ret - v0:+d} VBL after the click" if last_ret is not None else "no loader activity"), flush=True)


def cache_table(h):
    cur = h.peekl(PR.CURSOR)
    ents = []
    for r in range(NRES):
        a = h.peekl(E040 + 4 * r)
        if a:
            ents.append((r, a, h.peekl(E084 + 4 * r)))
    return cur, ents


def fmt_table(t):
    cur, ents = t
    return f"cursor ${cur:x}; " + ", ".join(f"res {r} @${a:x}+${s:x}" for r, a, s in ents)


class Run:
    def __init__(self, h):
        self.h = h
        self.ev = []
        self.t0 = time.time()

    def mark(self, label, v0, v1, extra=""):
        self.ev.append((label, v0, v1))
        print(f"TIME {label}: {v1 - v0} VBL ({v0} -> {v1}){extra}   [wall {time.time() - self.t0:.0f} s]", flush=True)

    def timed_click(self, label, xy, gate=None, until=None, timeout=150, poll=0.7):
        h = self.h
        h.goto_st(*xy)
        v0 = vbl(h)
        h.click(hold=0.2)
        t = time.time()
        while time.time() - t < timeout:
            time.sleep(poll)
            try:
                if (gate and h.at(gate)) or (until and until()):
                    break
            except RuntimeError:
                pass
        else:
            raise RuntimeError(f"{label}: screen never reached")
        v1 = vbl(h)
        self.mark(label, v0, v1)
        return v1 - v0


def boot(run: Run, name="Bench"):
    h = run.h
    t0 = time.time()
    time.sleep(15)
    if not h.wait_gate("name", 400, 4.0, act=lambda: h.key("space")):
        raise RuntimeError("name prompt not reached")
    arm_trace(h)
    print(f"RESULT name prompt after {time.time() - t0:.0f} s wall, vbl {vbl(h)}", flush=True)
    time.sleep(1.0)
    for ch in name:
        h.key(ch)
        time.sleep(0.25)
    h.key("Return")
    if not h.wait_gate("options", 40, 1.0):
        raise RuntimeError("option screen not reached")
    print(f"RESULT option screen, vbl {vbl(h)}", flush=True)
    time.sleep(1.0)
    run.timed_click("options -> territory chart (START NEW CONQUEST)", pm.START_NEW_XY, gate="chart")
    if h.protection_removed():
        run.timed_click("chart -> 3D map view (island click, level load)", pm.ISLAND_XY, gate="game", timeout=200)
    else:        # the original disk: the manual question first (answered from RAM, as pm.boot_to_game); the load time is the click on OK -> map view
        h.click_st(*pm.ISLAND_XY, wait=1.0)
        if not h.wait_gate("prot", 120, 1.0):
            raise RuntimeError("protection question not reached")
        typ, ans = h.protection_answer()
        digits = [(ans // 1000) % 10, (ans // 100) % 10, (ans // 10) % 10, ans % 10]
        for x, n in zip(pm.PROT_DIGIT_X, digits):
            if n:
                h.goto_st(x, pm.PROT_UP_Y)
                for _ in range(n):
                    h.click(hold=0.15)
                    time.sleep(0.4)
        run.timed_click("protection OK -> 3D map view (level load)", pm.PROT_OK_XY, gate="game", timeout=200)
    if not h.in_game():
        raise RuntimeError("HUD visible but main loop not iterating")


def level_again(run: Run, win: bool, rnd: str, neutral: bool = False):
    """After the picture: click -> option screen (or, as the game does after some retires, straight to the territory chart) ->
    START NEW CONQUEST (+ YES after a win) -> chart -> island -> map view."""
    h = run.h
    time.sleep(2.0)
    print(f"RESULT {rnd}: pointer at the picture click: {h.mpos()} (the option screen's START NEW CONQUEST is at {pm.START_NEW_XY})", flush=True)
    if not neutral:          # park the pointer where no button of the next screen is (a click held past the screen change would press it)
        h.goto_st(300, 190)
    v0 = vbl(h)
    h.click(hold=0.3)
    t = time.time()
    clicks = 1
    where = None
    while where is None:
        if h.at("options"):
            where = "options"
        elif h.at("chart"):
            where = "chart"
        if where:
            break
        if time.time() - t > 20 * clicks:
            if clicks >= 3:
                raise RuntimeError("neither the option screen nor the chart after the picture (3 clicks)")
            try:
                print(f"RESULT {rnd}: no option screen / chart 20 s after click {clicks}; cpu: " + h.debug("r", 0.8)[-300:].replace("\n", " | "), flush=True)
                h.shot(str(Path(h.R) / f"noopt_{rnd}_{clicks}.png"))
            except Exception:  # noqa: BLE001
                pass
            clicks += 1
            h.click(hold=0.3)
        time.sleep(0.7)
    if clicks > 1:
        print(f"RESULT {rnd}: needed {clicks} clicks (harness click lost)", flush=True)
    run.mark(f"{rnd}: picture click -> {'option screen' if where == 'options' else 'TERRITORY CHART (no option screen)'}", v0, vbl(h))
    if where == "options":
        time.sleep(1.0)
        h.goto_st(*pm.START_NEW_XY)
        v0 = vbl(h)
        h.click(hold=0.2)
        time.sleep(2.5)
        if win:
            dlg = not h.at("options")
            print(f"RESULT {rnd}: confirm dialog (screen no longer the option screen): {dlg}", flush=True)
            h.click_st(130, 111, wait=0.5)                      # YES: 'delete all of your conquered lands'
        t = time.time()
        while not h.at("chart"):
            if time.time() - t > 120:
                raise RuntimeError("territory chart not reached")
            time.sleep(0.7)
        run.mark(f"{rnd}: START NEW CONQUEST -> territory chart", v0, vbl(h))
    run.timed_click(f"{rnd}: chart -> 3D map view (2nd level load)", pm.ISLAND_XY, gate="game", timeout=200)
    if not h.in_game():
        raise RuntimeError("HUD visible but main loop not iterating")


def retire(run: Run, kind: str, rnd: str, shots, blobs):
    h = run.h
    win = kind in ("win", "final")
    h.click_st(*PR.OPTION_XY, wait=1.0)
    p = PR.wait_btn(h, "pm_btn_game.png")
    if p is None:
        raise RuntimeError("GAME button not found")
    h.click_st(*p, wait=1.0)
    p = PR.wait_btn(h, "pm_btn_retire.png")
    if p is None:
        raise RuntimeError("RETIRE button not found")
    if win:
        pokes = f"w ${PR.BALANCE:x} $00 $04\n" + ("w $2df6e $00 $04\nw $580a4 $00 $c2\n" if kind == "final" else "")
        (h.R / "win.txt").write_text(pokes)
        h.cmd(f"hatari-debug b pc = $d2d8 :trace :once :file {h.R / 'win.txt'}")
    h.goto_st(*p)
    v0 = vbl(h)
    h.click(hold=0.2)
    t = time.time()
    seen = 0
    best = (0.0, 0)
    first = None
    while time.time() - t < 150:
        try:
            frac, ncol = PR.shot_stats(h)
        except RuntimeError:
            frac, ncol = 0.0, 0
        best = max(best, (frac, ncol))
        if frac > 0.30 and ncol >= 12:
            if first is None:
                first = vbl(h)
            seen += 1
            if seen >= 3:
                break
        else:
            seen = 0
        time.sleep(0.5)
    ok = seen >= 3
    if first is not None:
        run.mark(f"{rnd} {kind}: RETIRE click -> first picture-like frame (poll only; the load itself: see the loader return)", v0, first)
    time.sleep(8.0)
    try:
        frac, ncol = PR.shot_stats(h)
    except RuntimeError:
        frac, ncol = 0.0, 0
    still = frac > 0.30 and ncol >= 12
    print(f"RESULT {rnd} {kind}: picture shown {ok}, still shown after 8 s {still} (non-black {frac:.2f}, {ncol} colours)", flush=True)
    if shots:
        try:
            h.shot(str(shots / f"{rnd}_{kind}_picture.png"))
        except RuntimeError:
            pass
    good = ok and still
    if kind == "final":      # the ending sequence runs on (END.DAT, 73 KB, is the second picture): look again after a minute
        time.sleep(60.0)
        try:
            frac2, ncol2 = PR.shot_stats(h)
            if shots:
                h.shot(str(shots / f"{rnd}_final_picture_60s.png"))
        except RuntimeError:
            frac2, ncol2 = 0.0, 0
        cpu = h.debug("r", 0.8)
        parked = "STP=1" in cpu
        print(f"RESULT {rnd} final: 68 s after the click: non-black {frac2:.2f}, {ncol2} colours, CPU parked in STOP: {parked}", flush=True)
        good &= frac2 > 0.05 and not parked
    if blobs:
        n, bad = PR.payload_report(h, blobs)
        print(f"RESULT {rnd} {kind}: payload {n} blobs, {len(bad)} differ {bad}", flush=True)
        good &= not bad
    print(f"RESULT {rnd} {kind}: cache {fmt_table(cache_table(h))}", flush=True)
    return good


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--disk")
    ap.add_argument("--hd")
    ap.add_argument("--acsi", action="store_true")
    ap.add_argument("--machine", default="megaste")
    ap.add_argument("--tos", default="2.06")
    ap.add_argument("--mem", type=int, default=4096)
    ap.add_argument("--hopts", default="")
    ap.add_argument("--seq", default="none", help="comma list of lose / win / final (or none)")
    ap.add_argument("--manifest")
    ap.add_argument("--fill", action="store_true", help="pattern in the free spans of $B8800..$EFFFF from the hand-over on (needs --manifest)")
    ap.add_argument("--shots")
    ap.add_argument("--idle", type=int, default=0, help="seconds to leave the game running in the last map view")
    ap.add_argument("--keep-pointer", action="store_true", help="click the picture where the pointer is (the Retire button) instead of parking it first")
    ap.add_argument("--workdir")
    a = ap.parse_args()
    seq = [] if a.seq == "none" else a.seq.split(",")
    kind = "HD" + ("-acsi" if a.acsi else "-gemdos") if a.hd else "floppy"
    name = f"{kind} {a.machine} TOS {a.tos} {a.mem} KB seq={a.seq}{' fill' if a.fill else ''}"
    print(f"CELL {name}", flush=True)
    shots = Path(a.shots) if a.shots else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    h, ok = None, True
    try:
        kw = dict(machine=a.machine, tos=TOS[a.tos], memsize_kb=a.mem, extra=shlex.split(a.hopts))
        if a.workdir:
            kw["workdir"] = a.workdir
        h = pmpatch.make_pm(Path(a.disk).resolve() if a.disk else None, Path(a.hd).resolve() if a.hd else None, acsi=a.acsi, **kw)
        blobs, spans, swap = [], [], None
        if a.manifest:
            import json
            man = json.loads(Path(a.manifest).read_text())
            for p in [p for p in pmpatch.load_all() if p.name in man["patches"]]:
                for org, lines in p.segments:
                    if org != p.site:
                        blobs.append((p.name, org, pmpatch.assemble(org, lines, "\n".join(p.preamble))))
            if a.fill:
                spans = pmpatch.free_spans(Path(a.manifest))
                if a.hd:           # the swap buffer may spill past $EFFFF (hd_core.s SMAX): the rest of $F0000..$F5FFF holds the pattern too (as pmpatch.cmd_boot)
                    t = time.time()
                    while h.peekl(0xBC000) != int.from_bytes(b"HDSW", "big"):
                        if time.time() - t > 120:
                            raise TimeoutError("hd_core init never set READY")
                        time.sleep(2)
                    s_end = (pmpatch.HD_SWAP_BASE + h.peekl(0xBC008) + 3) & ~3
                    if s_end < pmpatch.HD_SWAP_END:
                        spans.append((max(s_end, pmpatch.IMG_END), pmpatch.HD_SWAP_END))
                    swap = (pmpatch.HD_SWAP_BASE, pmpatch.HD_SWAP_BASE + h.peekl(0xBC008))
                lines = []
                for i, (lo, hi) in enumerate(spans):
                    f = h.R / f"f{i}.bin"
                    f.write_bytes(bytes(pmpatch.fill_byte(x) for x in range(lo, hi)))
                    lines.append(f"loadbin {f} ${lo:x}")
                (h.R / "fill.txt").write_text("\n".join(lines) + "\n")
                base, first = (pmpatch.BASE2, 0x41F9) if a.hd else (pmpatch.BASE1, 0x4EB9)      # HD: the proof starts at the game's hand-over (stage 1 is read through the overlay window)
                h.cmd(f"hatari-debug b pc = ${base:x} && (${base:x}).w = ${first:x} :trace :once :file {h.R / 'fill.txt'}")
                print(f"  fill armed at the stage {2 if a.hd else 1} hand-over: {len(spans)} span(s), {sum(hi - lo for lo, hi in spans)} bytes", flush=True)
        run = Run(h)
        t0 = time.time()
        boot(run)
        marker = h.peekl(pmpatch.MARKER).to_bytes(4, "big")
        try:
            sync = h.peekw(0xFF820A) >> 8
        except Exception:  # noqa: BLE001
            sync = None
        print(f"RESULT boot {time.time() - t0:.0f} s wall, MARKER {marker!r}, shifter sync reg ${sync if sync is None else format(sync, 'x')} (bit 1: 50 Hz)", flush=True)
        print(f"RESULT cache after the first level: {fmt_table(cache_table(h))}", flush=True)
        if blobs:
            n, bad = PR.payload_report(h, blobs)
            print(f"RESULT map view: payload {n} blobs, {len(bad)} differ {bad}", flush=True)
            ok &= not bad
        if spans:
            ok &= pmpatch.fill_report("map view", h.ram(0, 0x100000), spans, swap)
        for i, k in enumerate(seq, 1):
            rnd = f"r{i}"
            good = retire(run, k, rnd, shots, blobs)
            ok &= good
            if spans:
                ok &= pmpatch.fill_report(f"after {k} picture", h.ram(0, 0x100000), spans, swap)
            if not good:
                try:
                    print("  cpu:", h.debug("r", 0.8)[-420:].replace("\n", " | "), flush=True)
                except Exception:  # noqa: BLE001
                    pass
                break
            if k == "final":
                break
            level_again(run, k == "win", rnd, a.keep_pointer)
            if blobs:
                n, bad = PR.payload_report(h, blobs)
                print(f"RESULT {rnd} next level: payload {n} blobs, {len(bad)} differ {bad}", flush=True)
                ok &= not bad
            if spans:
                ok &= pmpatch.fill_report(f"{rnd} next level", h.ram(0, 0x100000), spans, swap)
        if a.idle and ok:
            time.sleep(a.idle)
            ok &= h.in_game()
            print(f"RESULT idle {a.idle} s in the last map view: main loop iterating {ok}", flush=True)
        print(f"RESULT cache at the end: {fmt_table(cache_table(h))}", flush=True)
        ev = trace_events(h)
        print(f"TRACE {len(ev)} loader events after the name prompt", flush=True)
        loader_summary(run, ev)
        print("TRACE raw (vbl kind d2.w):", " ".join(f"{v}/{k}/{'' if d is None else format(d & 0xFFFF, 'x')}" for v, k, d in ev), flush=True)
        if shots:
            try:
                h.shot(str(shots / "end.png"))
            except RuntimeError:
                pass
        print(f"CELL DONE {name}: {'OK' if ok else 'FAIL'}", flush=True)
        return 0 if ok else 2
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        try:
            if h is not None and shots:
                h.shot(str(shots / "fail.png"))
        except Exception:  # noqa: BLE001
            pass
        print(f"CELL FAILED {name}: {e!r}", flush=True)
        return 1
    finally:
        if h is not None:
            h.close()


if __name__ == "__main__":
    sys.exit(main())
