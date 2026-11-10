#!/usr/bin/env python3
"""PMBusErr: reproduce / gate the VBL pointer bus error (work/notes/buserr.md).

    python3 tools/pmbuserr.py repro SNAP [--set NAMES..] [--mhz 8] [--vbls 600] [--trace acia,ikbd] [--out DIR]
"""
from __future__ import annotations
import argparse, json, re, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE)]
import pmab  # noqa: E402
from pmab import make_live, apply_cmds, snap_path, at_vbl_for, make_pm, memsize_of, TICK  # noqa: E402

DEFAULTS = TICK + ["p4_ptr_a", "p4_ptr_b", "p4_spr", "p6_cpy"]


def repro(a):
    sp = snap_path(a.snap)
    names = a.set if a.set is not None else DEFAULTS
    live = make_live(names)
    at = at_vbl_for(sp)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    extra = ["--trace-file", str(out / "trace.txt")] if a.trace else []
    h = make_pm(snapshot=str(sp), memsize_kb=memsize_of(sp), workdir=str(out / "run"), extra=extra)
    try:
        R = h.R
        time.sleep(1.0)
        if a.mhz != 8:
            h.set_cpuclock(a.mhz)
        cmds = apply_cmds(live)
        for pk in a.poke:
            ad, hx = pk.split(":")
            cmds.append(f"w ${int(ad, 16):x} " + " ".join(f"${hx[i:i + 2]}" for i in range(0, len(hx), 2)))
        if a.trace:
            cmds.append(f"trace {a.trace}")
        (R / "bad.txt").write_text("r\ne VBL\ne CycleCounter\nm $2df78 24\nm $1c48e 8\nm $1c490 8\nm $fffc00 4\nm $cef20 12\n")
        cmds.append(f"b pc = $147c && a4 > $f0000 :trace :once :file {R / 'bad.txt'}")
        for i, pc in enumerate(a.count):
            (R / f"cnt{i}.txt").write_text("e VBL\nm $1c492 4\nm $2df92 4\n")
            cmds.append(f"b pc = ${pc} :trace :file {R / f'cnt{i}.txt'}")
        (R / "end.txt").write_text(f"b all\nsavebin {out}/end.flag $0 2\ne VBL\nm $cef20 12\n")
        cmds.append(f"b VBL > {at + a.vbls} :trace :once :file {R / 'end.txt'}")
        (R / "apply.txt").write_text("\n".join(cmds) + "\n")
        for f in out.glob("end.flag"):
            f.unlink()
        h.cmd(f"hatari-debug b VBL > {at} && pc = ${pmab.APPLYPC:x} :trace :once :file {R / 'apply.txt'}")
        time.sleep(0.3)
        h.cmd("hatari-option --fast-forward on")
        t = time.time()
        while not (out / "end.flag").exists():
            txt = h._logtext()
            if "Bus Error" in txt or "bus error" in txt.lower():
                time.sleep(1)
                break
            if time.time() - t > a.timeout:
                print("TIMEOUT"); break
            time.sleep(0.5)
        time.sleep(0.5)
        txt = h._logtext()
        (out / "log.txt").write_text(txt)
        for i, pc in enumerate(a.count):
            print(f"breakpoint pc=${pc}: {txt.count(f'cnt{i}.txt' + chr(39) + '...')} hits")
        print(txt[-2500:] if not a.quiet else "")
    finally:
        h.close()


def default_names():
    import pmpatch
    return [p.name for p in pmpatch.load_all() if p.default]


def build(names, out):
    import subprocess
    out = Path(out)
    subprocess.run([sys.executable, str(HERE / "pmpatch.py"), "build", "--floppy", "--only", *names, "--out", str(out)], check=True,
                   cwd=HERE.parent, stdout=subprocess.DEVNULL)
    return out / "floppy" / "powermonger.st"


def stress(a):
    """Cold boot of a floppy build (defaults + test_ovr; --old: p6_cpy replaced by the 10-row chunk version) and a stress of host mouse /
    key events for --minutes of wall time from the map view through get_men and the battle.  Prints the ACIA overrun counter of test_ovr."""
    import random, threading, subprocess
    import pmpatch
    names = [n for n in default_names() if not (a.old and n == "p6_cpy") and n not in a.no] + (["test_cpyold"] if a.old else []) + ["test_ovr"] + a.extra
    disk = build(names, a.out + "/b")
    print("patch set:", " ".join(names), flush=True)
    sys.path.insert(0, str(HERE))
    import pm
    h = pmpatch.make_pm(disk, None, machine="ste", tos=pm.TOS["1.62"], memsize_kb=1024)
    stop = threading.Event()
    print("run dir:", h.R, flush=True)
    try:
        t0 = time.time()
        h.boot_to_game()
        print(f"in game after {time.time() - t0:.0f}s, FLAGS={h.peekl(pmpatch.FLAGS):#x}", flush=True)

        def ovr():
            txt = h.debug("m $cef20 12", 0.6)
            m = re.search(r"000CEF20: ((?:[0-9a-f]{2} ){12})", txt)
            b = bytes.fromhex(m.group(1).replace(" ", "")) if m else b""
            return (int.from_bytes(b[0:2], "big"), int.from_bytes(b[2:6], "big"), int.from_bytes(b[6:10], "big")) if len(b) >= 10 else None

        if a.mhz != 8:
            h.set_cpuclock(a.mhz)
        print("after boot: (overruns, bytes, vbl of last)", ovr(), flush=True)
        if a.getmen:
            n = h.scenario_get_men()
            print("get_men moving:", n, "ovr", ovr(), flush=True)

        rnd = random.Random(1)

        def mover():
            n = 0
            while not stop.is_set():
                dx, dy = rnd.randint(-60, 60), rnd.randint(-40, 40)
                h._xdo("mousemove_relative", "--", str(dx), str(dy))      # relative motion: the game sees mouse deltas, as from a real mouse
                n += 1
                if n % 40 == 0:
                    h._xdo("mousemove", "--window", h.win, "416", "294")
                if rnd.random() < a.keys:
                    h._xdo("key", "--window", h.win, rnd.choice(["Shift_L", "Control_L", "Up", "Down", "Left", "Right"]))
        th = [threading.Thread(target=mover, daemon=True) for _ in range(a.threads)]
        for t in th:
            t.start()
        t1 = time.time()
        bad = 0
        while time.time() - t1 < a.minutes * 60:
            time.sleep(15)
            txt = h._logtext()
            be = txt.count("Bus Error") + txt.count("Address Error")
            try:
                x, y = h.peekw(pm.MOUSE_X), h.peekw(pm.MOUSE_Y)
                px, py = h.peekw(0x2DF92), h.peekw(0x2DF94)
                print(f"t={time.time() - t1:5.0f}s iter={h.iter_count()} ovr={ovr()} ptr=({px},{py}) ikbd=({x},{y}) bus/addr errors in log={be}", flush=True)
            except (IndexError, ValueError):      # the debugger's answer came late on a loaded host: skip this sample
                print(f"t={time.time() - t1:5.0f}s (sample skipped) bus/addr errors in log={be}", flush=True)
            if be:
                bad = 1
                break
        stop.set()
        for t in th:
            t.join()
        print("FINAL ovr", ovr(), "errors", h._logtext().count("Bus Error"), flush=True)
        h.shot(a.out + "/final.png")
        return bad
    finally:
        stop.set()
        h.close()


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("repro")
    r.add_argument("snap")
    r.add_argument("--set", nargs="*", default=None)
    r.add_argument("--mhz", type=int, default=8)
    r.add_argument("--vbls", type=int, default=600)
    r.add_argument("--trace", default="")
    r.add_argument("--out", default="/tmp/pmbe/r1")
    r.add_argument("--count", nargs="*", default=[], help="hex pcs: count the hits of a breakpoint")
    r.add_argument("--quiet", action="store_true")
    r.add_argument("--poke", action="append", default=[])
    r.add_argument("--timeout", type=int, default=300)
    st = sub.add_parser("stress")
    st.add_argument("--old", action="store_true")
    st.add_argument("--minutes", type=float, default=5)
    st.add_argument("--out", default="/tmp/pmbe/st1")
    st.add_argument("--extra", nargs="*", default=[])
    st.add_argument("--no", nargs="*", default=[], help="default patches to leave out (p4_clamp: the control without the safety net)")
    st.add_argument("--threads", type=int, default=2)
    st.add_argument("--keys", type=float, default=0.02)
    st.add_argument("--getmen", action="store_true")
    st.add_argument("--mhz", type=int, default=8)
    a = ap.parse_args()
    sys.exit({"repro": repro, "stress": stress}[a.cmd](a) or 0)


if __name__ == "__main__":
    main()
