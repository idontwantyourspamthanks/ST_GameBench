#!/usr/bin/env python3
"""50/60 Hz gates for Hunter (patch hn_hz, work/notes/timing.md).

    python3 games/done/hunter/tools/hunthz.py ab   --snapshot foot_walk --hold up   --vbls 600 [--lock] [--mhz 8]
    python3 games/done/hunter/tools/hunthz.py rate --snapshot car_stand --hold up   --mhz 8 --hz 50 60 [--set ...]
    python3 games/done/hunter/tools/hunthz.py table [--hz 50 60] [--mhz 8 16]      (gate b: base vs hn_hz, foot / car / car turn)
    python3 games/done/hunter/tools/hunthz.py drv                                   (original driver ticks per VBL, STE and plain ST)
    python3 games/done/hunter/tools/hunthz.py cold --kind hd --game build/game --machine ste --tos 1.62 --mem 1024 [--hz 50 60] --mhz 8 16
    python3 games/done/hunter/tools/hunthz.py cold --kind floppy --game build/floppy/HUNTER_disk1.st ...
    ab --control: base = patch test_hznop (same cost as hn_hz, never skips): bit-identical frames expected at 50 Hz (gate a)

Both runs restore the snapshot, and at the first flip ($5fee) after a start VBL apply the live patch set (`huntpatch.py live`),
optionally force the refresh with `w $ff820a $00` (60 Hz) and hold the stick: every VBL, at `$c64c` (the handler's joystick copy
`$d1 -> $d0`), the debugger pokes `$d1(a5)` ($8d7) so the game sees a constant stick state in BOTH runs (a host key press is not
reproducible to the VBL).  At every loop top `$253e` the VBL counter, the cycle counter and the game's RAM are logged.
  ab   : base set (default patches without hn_hz) vs base+hn_hz at 50 Hz (or --hz): the per-frame game state must be identical.
  rate : world rates per REAL second (player X/Z/heading, game clock, tick counter $1a8) of base+hn_hz at 50 and 60 Hz.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path[:0] = [str(GAME.parent.parent.parent / "tools"), str(HERE)]
from hunter import Hunter, SNAP  # noqa: E402

LOOP = 0x253E                       # frame loop top
FLIP = 0x5FEE
JOY_COPY = 0xC64C                   # `move.b $d1(a5),d0`: the handler's copy of the stick state (a5 = $806)
D1 = 0x806 + 0xD1                   # $d1(a5)
STICK = {"up": 0x02, "upleft": 0x0A, "none": None}   # upleft: see `probe` below (bits are measured, not assumed)
A5 = 0x806
STATE_LO, STATE_LEN = 0x806, 0x152A            # the game variables and the 30 object records ($a68 + 30 x $a0 = $1d28)
SHORT = {"foot_stand": "1mb_foot_stand", "foot_walk": "1mb_foot_walk", "car_stand": "1mb_car_stand",
         "car_drive": "1mb_car_drive", "car_turn": "1mb_car_turn", "hills_stand": "1mb_hills_stand",
         "4mb_foot_stand": "4mb_foot_stand"}
BASE_SET = ["p4_ikbd", "p4_edge", "p4_poly", "snd_core"]
NUM = re.compile(r"#(\d+) \(dec\)")
ROW = re.compile(r"^([0-9A-F]{8}):\s+((?:[0-9a-f]{2} )+)", re.M)
WORK = Path("/tmp/hunhz")


def make_live(names: list[str], tag: str, samples: bool = True, extra: list[str] | None = None) -> str | None:
    if not names:
        return None
    live = WORK / tag / "live"
    live.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(HERE / "huntpatch.py"), "live", "--only", *names, "--out", str(live)]
    if samples and (GAME / "build" / "hunter_snd.bin").exists():
        cmd += ["--samples", str(GAME / "build" / "hunter_snd.bin")]
    cmd += extra or []
    subprocess.run(cmd, check=True, cwd=GAME, stdout=subprocess.DEVNULL)
    jp = Path(str(live) + ".json")
    spec = json.loads(jp.read_text())
    sites = []
    for st in spec["sites"]:
        raw = bytes.fromhex(st["new"])
        for o in range(0, len(raw), 40):
            sites.append({**st, "addr": st["addr"] + o, "new": raw[o:o + 40].hex()})
    spec["sites"] = sites
    jp.write_text(json.dumps(spec, indent=1))
    return str(live)


def snap_path(s: str) -> Path:
    return SNAP / f"{SHORT.get(s, s)}.sav"


def parse(text: str) -> list[dict]:
    rows = []
    for blk in text.split("CPU breakpoint condition(s) matched")[1:]:
        nums = NUM.findall(blk)
        if f"pc = ${LOOP:x}" not in blk or len(nums) < 2:
            continue
        mem = {}
        for a, bs in ROW.findall(blk):
            mem[int(a, 16)] = bytes(int(x, 16) for x in bs.split())
        data = bytearray(STATE_LEN)
        for a, b in mem.items():
            if STATE_LO <= a < STATE_LO + STATE_LEN:
                data[a - STATE_LO:a - STATE_LO + len(b)] = b[:STATE_LO + STATE_LEN - a]
        rows.append({"vbl": int(nums[0]), "cyc": int(nums[1]), "mem": bytes(data)})
    return rows


def trace(snap: str, names: list[str] | None, hz: int, mhz: int, vbls: int, hold: str, tag: str, lock: bool = False,
          live: str | None = None, pokes: list[str] | None = None, region=(STATE_LO, STATE_LEN), h=None,
          force60: bool | None = None) -> dict:
    """Restore `snap` (or use the running instance `h`: a cold-booted game), apply the live patch set and the pokes at the next
    flip, and log every loop top for `vbls` VBLs.  hz = 60 forces the refresh with `w $ff820a $00`; hz = 0 leaves it alone."""
    own = h is None
    if own:
        sp = snap_path(snap)
        h = Hunter(snapshot=str(sp), memsize_kb=4096 if snap.startswith("4mb") else 1024)
    try:
        R = h.R
        if own and mhz != 8:
            h.set_cpuclock(mhz)
        live = live if live is not None else make_live(names or [], tag) if own else None
        if STICK.get(hold) is not None:
            (R / "joy.txt").write_text(f"w ${D1:x} ${STICK[hold]:02x}\n")
        (R / "top.txt").write_text(f"e VBL\ne CycleCounter\nm ${region[0]:x} {region[1]}\n")
        cmds = ["e VBL", "e CycleCounter"]
        if live:
            spec = json.loads(Path(live + ".json").read_text())
            cmds.append(f"loadbin {Path(live + '.img')} ${spec['img_base']:x}")
            for s in spec["sites"]:
                cmds.append(f"w ${s['addr']:x} " + " ".join(f"${b:02x}" for b in bytes.fromhex(s["new"])))
        if (hz == 60) if force60 is None else force60:
            cmds.append("w $ff820a $00")
        if lock:
            cmds.append("w $9ad $0e")
        cmds += pokes or []
        if STICK.get(hold) is not None:
            cmds.append(f"b pc = ${JOY_COPY:x} :trace :file {R / 'joy.txt'}")
        cmds.append(f"b pc = ${LOOP:x} :trace :file {R / 'top.txt'}")
        v0 = h.vbl()
        at = v0 + 40
        end = R / "end.txt"
        end.write_text("b all\n")
        cmds.append(f"b VBL > {at + vbls} :trace :once :file {end}")
        app = R / "apply.txt"
        app.write_text("\n".join(cmds) + "\n")
        if len(max(cmds, key=len)) > 235:
            raise ValueError("debugger command line too long")
        start = len(h._logtext())
        h.cmd(f"hatari-debug b VBL > {at} && pc = ${FLIP:x} :trace :once :file {app}")
        time.sleep(0.3)
        if own:
            h.cmd("hatari-option --fast-forward on")
        t = time.time()
        while h._logtext()[start:].count("Removed CPU breakpoint") < 2:
            if time.time() - t > (900 if own else 3600):
                raise TimeoutError(h._logtext()[-1500:])
            time.sleep(0.5)
        time.sleep(0.5)
        text = h._logtext()[start:]
    finally:
        if own:
            h.close()
    rows = [r for r in parse(text) if any(r["mem"])]      # a block whose `m` output was lost reads as all zero
    return {"rows": rows, "text_len": len(text)}


# ---- decoding ---------------------------------------------------------------------------------------------------
def w(mem: bytes, addr: int, n: int = 2, signed=False) -> int:
    o = addr - STATE_LO
    return int.from_bytes(mem[o:o + n], "big", signed=signed)


def s16d(a: int, b: int) -> int:
    d = (b - a) & 0xFFFF
    return d - 0x10000 if d >= 0x8000 else d


def slope(ts: list[float], ys: list[float]) -> float:
    n = len(ts)
    mt, my = sum(ts) / n, sum(ys) / n
    den = sum((t - mt) ** 2 for t in ts)
    return sum((t - mt) * (y - my) for t, y in zip(ts, ys)) / den if den else 0.0


def unwrap(vals: list[int]) -> list[int]:
    out = [0]
    for p, c in zip(vals, vals[1:]):
        out.append(out[-1] + s16d(p, c))
    return out


def rates(rows: list[dict], hz: int, ta: float = 2.0, tb: float = 9.0) -> dict:
    """World rates per REAL second over the window [ta, tb] s after the first loop top: least-squares slope of the 16-bit word
    (unwrapped) against t = VBL / hz at every loop top, so that the frame quantisation does not bias the endpoints."""
    v0 = rows[0]["vbl"]
    win = [r for r in rows if ta <= (r["vbl"] - v0) / hz <= tb]
    a, b = win[0], win[-1]
    dv = b["vbl"] - a["vbl"]
    sec = dv / hz
    ts = [(r["vbl"] - v0) / hz for r in win]
    out = {"frames": len(win), "vbl": dv, "sec": round(sec, 3), "fps": round((len(win) - 1) / sec, 3)}
    out["cycles_per_vbl"] = round((b["cyc"] - a["cyc"]) / dv)
    sx = slope(ts, unwrap([w(r["mem"], 0xAB2) for r in win]))
    sz = slope(ts, unwrap([w(r["mem"], 0xAB6) for r in win]))
    out["dX_u_s"], out["dZ_u_s"] = round(sx, 2), round(sz, 2)
    out["speed_u_s"] = round((sx * sx + sz * sz) ** 0.5, 2)
    out["heading_u_s"] = round(slope(ts, unwrap([w(r["mem"], 0xAE6) for r in win])), 1)
    tk = [w(r["mem"], 0x9AE) for r in win]                      # $1a8(a5): world tick counter (word)
    out["ticks_per_s"] = round(slope(ts, unwrap(tk)), 3)

    def clock(m):                                    # $1b2 counts 59..0 per tick, $1b4 minutes, $1b6 hours, $1b8 days
        mi, ho, da, c = w(m, 0x806 + 0x1B4), w(m, 0x806 + 0x1B6), w(m, 0x806 + 0x1B8), w(m, 0x806 + 0x1B2)
        return ((da * 24 + ho) * 60 + mi) * 60 + (59 - c if 0 <= c <= 59 else 0)
    out["clock_ticks_per_s"] = round(slope(ts, [clock(r["mem"]) for r in win]), 3)
    # per world tick (hz independent by construction of the check above): position change per tick over the same window
    dt = (w(b["mem"], 0x9AE) - w(a["mem"], 0x9AE)) & 0xFFFF
    out["speed_u_per_tick"] = round(((s16d(w(a["mem"], 0xAB2), w(b["mem"], 0xAB2))) ** 2 + (s16d(w(a["mem"], 0xAB6), w(b["mem"], 0xAB6))) ** 2) ** 0.5 / dt, 3) if dt else 0
    return out


def cmd_rate(a):
    names = a.set if a.set is not None else BASE_SET + ["hn_hz"]
    for hz in a.hz:
        for mhz in a.mhz:
            t = trace(a.snapshot, names, hz, mhz, int(a.secs * hz) if a.secs else a.vbls, a.hold, "rate_" + "_".join(names))
            rows = t["rows"]
            if len(rows) < 3:
                print(f"{a.snapshot} {hz} Hz {mhz} MHz: only {len(rows)} loop tops")
                continue
            r = rates(rows, hz, a.ta, a.tb)
            r.update(snapshot=a.snapshot, hold=a.hold, hz=hz, mhz=mhz, set=("+".join(n for n in names if n not in BASE_SET) or "base"))
            print("RESULT " + json.dumps(r), flush=True)


SCEN = [  # name, snapshot, stick, window [ta, tb] s, secs
    ("foot", "foot_walk", "up", 1.0, 9.0, 10),
    ("car", "car_stand", "up", 0.5, 3.0, 4),
    ("car_turn", "car_turn", "upleft", 0.5, 4.0, 5),
]


def cmd_table(a):
    """The gate (b) table: per scenario, base (no hn_hz) and base+hn_hz at 50/60 Hz and 8/16 MHz."""
    rows = []
    for nm, snap, hold, ta, tb, secs in SCEN:
        for label, names in (("base", BASE_SET), ("hn_hz", BASE_SET + ["hn_hz"])):
            if a.only and label not in a.only:
                continue
            for hz in a.hz:
                for mhz in a.mhz:
                    t = trace(snap, names, hz, mhz, int(secs * hz) + 20, hold, f"tab_{label}")
                    r = rates(t["rows"], hz, ta, tb)
                    r.update(scen=nm, set=label, hz=hz, mhz=mhz)
                    print("ROW " + json.dumps(r), flush=True)
                    rows.append(r)
    keyf = {"foot": "dZ_u_s", "car": "speed_u_s", "car_turn": "heading_u_s"}
    print("\nscenario  set    MHz | 50 Hz units/s | 60 Hz units/s | 60/50 | clock ticks/s 50 -> 60 | tick counter/s 50 -> 60")
    for nm in keyf:
        for label in ("base", "hn_hz"):
            for mhz in a.mhz:
                r50 = next((r for r in rows if r["scen"] == nm and r["set"] == label and r["hz"] == 50 and r["mhz"] == mhz), None)
                r60 = next((r for r in rows if r["scen"] == nm and r["set"] == label and r["hz"] == 60 and r["mhz"] == mhz), None)
                if r50 and r60:
                    k = keyf[nm]
                    print(f"{nm:9s} {label:6s} {mhz:3d} | {r50[k]:13} | {r60[k]:13} | {r60[k] / r50[k]:.4f} | "
                          f"{r50['clock_ticks_per_s']:.3f} -> {r60['clock_ticks_per_s']:.3f} | {r50['ticks_per_s']:.3f} -> {r60['ticks_per_s']:.3f}")


def cmd_ab(a):
    base = BASE_SET + (["test_hznop"] if a.control else [])
    pat = BASE_SET + ["hn_hz"]
    out = {}
    from concurrent.futures import ThreadPoolExecutor
    lb = make_live(base, "ab_ctl" if a.control else "ab_base")
    lp = make_live(pat, "ab_hz")
    with ThreadPoolExecutor(2) as ex:
        fb = ex.submit(trace, a.snapshot, base, a.hz[0], a.mhz[0], a.vbls, a.hold, "ab_ctl" if a.control else "ab_base", a.lock, lb)
        fp = ex.submit(trace, a.snapshot, pat, a.hz[0], a.mhz[0], a.vbls, a.hold, "ab_hz", a.lock, lp)
        rb, rp = fb.result()["rows"], fp.result()["rows"]
    n = min(len(rb), len(rp))
    # align on the VBL of the first loop top (both runs start at the same VBL: the apply flip)
    bad = []
    dvb = [b["vbl"] for b in rb[:n]]
    dvp = [p["vbl"] for p in rp[:n]]
    for i in range(n):
        if rb[i]["mem"] != rp[i]["mem"]:
            diff = [STATE_LO + j for j in range(STATE_LEN) if rb[i]["mem"][j] != rp[i]["mem"][j]]
            bad.append((i, rb[i]["vbl"], rp[i]["vbl"], diff[:12], len(diff)))
    print(f"AB {a.snapshot} hold={a.hold} {a.hz[0]} Hz {a.mhz[0]} MHz lock={a.lock} base={'timing control test_hznop' if a.control else 'unpatched'}: base {len(rb)} loop tops, patched {len(rp)} loop tops, "
          f"VBL {rb[0]['vbl']}..{rb[-1]['vbl']} / {rp[0]['vbl']}..{rp[-1]['vbl']}, compared {n} x {STATE_LEN} B")
    print(f"AB frame VBL sequence identical: {dvb == dvp}")
    firstdiv = next((i for i in range(n) if rb[i]["vbl"] != rp[i]["vbl"] or rb[i]["mem"] != rp[i]["mem"]), n)
    print(f"AB frames identical before the first difference: {firstdiv} of {n}")
    if bad:
        print(f"AB DIFFER in {len(bad)} of {n} frames; first: frame {bad[0][0]} VBL {bad[0][1]}/{bad[0][2]} {bad[0][4]} bytes at "
              + " ".join(f"${x:x}" for x in bad[0][3]))
    else:
        print(f"AB IDENTICAL: {n} of {n} frames, {a.vbls} VBL")
    return not bad


def cmd_cold(a):
    """Cold boot a build (HD folder or floppy disk), check the patch marker, then measure the world at 60 Hz (forced with a poke
    on a machine that boots at 50 Hz; native on the Mega STE) at each --mhz.  --hz 50 60 also measures the 50 Hz reference."""
    import re as _re
    from stharness import TOS
    import hunter
    h = None
    orig_build = hunter.build_hd
    try:
        if a.kind == "hd":
            gdir = (GAME / a.game).resolve()
            hunter.build_hd = lambda img, **k: orig_build(img, game=gdir, **k)
            h = hunter.Hunter(machine=a.machine, tos=TOS[a.tos], memsize_kb=a.mem, extra=["--sound", "50066"] if False else None)
        else:
            from huntfloppy import HunterFloppy
            h = HunterFloppy(str((GAME / a.game).resolve()), None, drives=1, machine=a.machine, tos=TOS[a.tos], memsize_kb=a.mem,
                             fastfdc=a.fastfdc)
        stage = h._stage
        t0 = time.time()
        syncs = []

        def _stage(s_, record, wait, timeout=120):
            r = stage(s_, record, wait, max(timeout, 600))
            try:
                syncs.append(f"{s_}:${h.peek(0xFF820A, 1)[0]:02x}")
            except Exception:  # noqa: BLE001
                pass
            return r
        h._stage = _stage
        if a.kind == "hd":
            h.boot_to_game()
        else:
            h.boot_floppy("none", pb_key_at=a.pb_at)
        boot = time.time() - t0
        mk, fl = h.peek(0x8BFF8, 4), h.peek(0x8BFF0, 4)
        sync = h.peek(0xFF820A, 1)[0]
        sv = h.peek(0x8F000, 4)
        hzs = h.peek(0x8DBF0, 4)
        print("COLD sync mode $ff820a after each boot stage (fe = 50 Hz, fc = 60 Hz): " + " ".join(syncs), flush=True)
        print(f"COLD {a.kind} {a.machine} TOS {a.tos} {a.mem} KB: boot {boot:.0f} s, in_game {h.in_game()}, marker {mk!r}, FLAGS {fl.hex()}, "
              f"sync $ff820a = ${sync:02x} -> {'50' if sync & 2 else '60'} Hz at boot, payload mode {sv[0]} (2 = DMA sound), "
              f"hn_hz state {hzs.hex()}", flush=True)
        native60 = not sync & 2
        for hz in a.hz:
            for mhz in a.mhz:
                h.set_cpuclock(mhz)
                t = trace("cold", None, hz, mhz, int(a.secs * hz) + 20, a.hold, "cold", live="", h=h,
                          force60=(hz == 60 and not native60))
                rows = t["rows"]
                # the refresh really is what we asked for: cycles per VBL = clock / hz
                r = rates(rows, hz, 1.0, a.secs)
                r.update(kind=a.kind, machine=a.machine, mem=a.mem, hz=hz, mhz=mhz)
                print("COLDROW " + json.dumps(r), flush=True)
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"COLD FAILED {a.kind} {a.machine}: {e!r}")
        if h is not None:
            try:
                h.shot(str(WORK / f"cold_fail_{a.kind}_{a.machine}.png"))
            except Exception:  # noqa: BLE001
                pass
        return 1
    finally:
        hunter.build_hd = orig_build
        if h is not None:
            h.close()


DRV_TICK = 0x10FF2                   # the sound driver's state machine entry ($10fb2 + $40; both the original and the snd_core path call it)


def cmd_drv(a):
    """How often the original sound driver tick runs per VBL: STE (DMA sound, mode 2) and plain ST (YM passthrough, mode 1), 50/60 Hz."""
    for ste in (True, False):
        live = make_live(["snd_core", "hn_hz"], "drv_ste" if ste else "drv_st", True, [] if ste else ["--no-ste"])
        for hz in a.hz:
            h = Hunter(snapshot=str(snap_path("foot_stand")))
            try:
                R = h.R
                (R / "drv.txt").write_text("e VBL\n")
                spec = json.loads(Path(live + ".json").read_text())
                cmds = ["e VBL", f"loadbin {Path(live + '.img')} ${spec['img_base']:x}"]
                cmds += ["w $%x " % s_["addr"] + " ".join(f"${b:02x}" for b in bytes.fromhex(s_["new"])) for s_ in spec["sites"]]
                if hz == 60:
                    cmds.append("w $ff820a $00")
                cmds.append(f"b pc = ${DRV_TICK:x} :trace :file {R / 'drv.txt'}")
                end = R / "end.txt"
                end.write_text("b all\n")
                v0 = h.vbl()
                at = v0 + 40
                cmds.append(f"b VBL > {at + a.vbls} :trace :once :file {end}")
                (R / "apply.txt").write_text("\n".join(cmds) + "\n")
                st = len(h._logtext())
                h.cmd(f"hatari-debug b VBL > {at} && pc = ${FLIP:x} :trace :once :file {R / 'apply.txt'}")
                time.sleep(0.3)
                h.cmd("hatari-option --fast-forward on")
                while h._logtext()[st:].count("Removed CPU breakpoint") < 2:
                    time.sleep(0.5)
                time.sleep(0.5)
                text = h._logtext()[st:]
                mode = h.peek(0x8F000, 1)[0]
            finally:
                h.close()
            blocks = [b for b in text.split("CPU breakpoint condition(s) matched")[1:] if re.match(r"\s*\d+ times\.\s*pc = \$%x" % DRV_TICK, b, re.I)]
            n = len(blocks)
            v = [int(re.search(r"#(\d+) \(dec\)", b).group(1)) for b in blocks]
            span = v[-1] - v[0] + 1 if v else 0
            print(f"DRV {'STE (DMA sound)' if ste else 'plain ST (YM)'} payload mode {mode} {hz} Hz: driver ticks {n} in {span} VBL = "
                  f"{n / span:.4f} per VBL = {n / span * hz:.2f} per second", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nm in ("ab", "rate"):
        p = sub.add_parser(nm)
        p.add_argument("--snapshot", default="foot_walk")
        p.add_argument("--hold", default="up", choices=sorted(STICK))
        p.add_argument("--vbls", type=int, default=600)
        p.add_argument("--secs", type=float, default=0, help="rate: run this many emulated seconds (vbls = secs x hz)")
        p.add_argument("--hz", nargs="*", type=int, default=[50])
        p.add_argument("--mhz", nargs="*", type=int, default=[8])
        p.add_argument("--lock", action="store_true")
        p.add_argument("--control", action="store_true", help="ab: base = the same-cost control patch test_hznop instead of the unpatched game")
        p.add_argument("--ta", type=float, default=2.0)
        p.add_argument("--tb", type=float, default=9.0)
        p.add_argument("--set", nargs="*", default=None)
    dp = sub.add_parser("drv")
    dp.add_argument("--hz", nargs="*", type=int, default=[50, 60])
    dp.add_argument("--vbls", type=int, default=600)
    tp = sub.add_parser("table")
    tp.add_argument("--hz", nargs="*", type=int, default=[50, 60])
    tp.add_argument("--mhz", nargs="*", type=int, default=[8, 16])
    tp.add_argument("--only", nargs="*", default=None, help="base and/or hn_hz")
    cp = sub.add_parser("cold")
    cp.add_argument("--kind", choices=["hd", "floppy"], default="hd")
    cp.add_argument("--game", required=True, help="HD: build dir (build/hz_game); floppy: the .st disk image path relative to games/done/hunter")
    cp.add_argument("--machine", default="ste")
    cp.add_argument("--tos", default="1.62")
    cp.add_argument("--mem", type=int, default=1024)
    cp.add_argument("--hz", nargs="*", type=int, default=[60])
    cp.add_argument("--mhz", nargs="*", type=int, default=[8, 16])
    cp.add_argument("--secs", type=float, default=8)
    cp.add_argument("--hold", default="up", choices=sorted(STICK))
    cp.add_argument("--fastfdc", default="no")
    cp.add_argument("--pb-at", type=float, default=12)
    a = ap.parse_args()
    WORK.mkdir(exist_ok=True)
    if a.cmd == "cold":
        sys.exit(cmd_cold(a))
    if a.cmd == "drv":
        cmd_drv(a)
        return
    if a.cmd == "table":
        cmd_table(a)
        return
    if a.cmd == "ab":
        sys.exit(0 if cmd_ab(a) else 1)
    cmd_rate(a)


if __name__ == "__main__":
    main()
