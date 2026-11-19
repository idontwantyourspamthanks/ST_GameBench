"""Hatari `--trace fdc` parser for the Midwinter 2 floppy gates.

Trace lines used (Hatari 2.6.1-devel):
  fdc type I restore spinup=on verify=on steprate_ms=12 drive=0 tr=0x2e head_track=0x2e VBL=3298 video_cyc=23928 376@46 pc=27c4e
  fdc type I seek dest_track=0x1 ... tr=.. head_track=..                      (also `step`, `step in`)
  fdc type II read sector ... / fdc type IV force int 0xd4 irq=0 index=0 VBL=.. video_cyc=.. pc=27c4e
  fdc complete command VBL=.. video_cyc=..
  fdc update index drive=0 side=0 counter=1 ip_time=528968904 VBL=3301 HBL=112
Time base: 8 021 247 cycles/s.  ip_time and video_cyc count CPU cycles, so a 16 MHz CPU doubles them (one revolution = 1 604 249 x mult
cycles, 200 ms); the multiplier is read from the index pulses near each event.  The frame length (HBL lines: 313 at 50 Hz, 262 at 60 Hz)
comes from the index pulses too.
"""
import bisect
import re
from statistics import median

CPS = 8021247.0
REV = 1604249                # cycles per revolution at 8 MHz (200 ms)
RE_VBL = re.compile(r"VBL=(\d+)")
RE_CYC = re.compile(r"video_cyc=(\d+)")
RE_HBL = re.compile(r"HBL=(\d+)")
RE_PC = re.compile(r"pc=([0-9a-f]+)")
RE_IDX = re.compile(r"ip_time=(\d+) VBL=(\d+) HBL=(\d+)")
GAME_PC = "27c4e"            # `move.w d7,$ff8604` of the game's sub_027c4a: every game FDC command and force interrupt


def _mult_of(dt):
    for m in (1, 2, 4):
        if abs(dt - REV * m) < 0.02 * REV * m:
            return m
    return None


def analyse_clock(raw):
    """-> (L, [(VBL, mult)]): frame length in HBL lines, CPU clock multiplier near each index line."""
    pts = []
    for ln in raw:
        if ln.startswith("fdc update index"):
            m = RE_IDX.search(ln)
            if m:
                pts.append(tuple(int(x) for x in m.groups()))
    mults, ests = [], []
    for (t0, v0, h0), (t1, v1, h1) in zip(pts, pts[1:]):
        m = _mult_of(t1 - t0)
        if m:
            mults.append((v1, m))
    for (t0, v0, h0), (t1, v1, h1) in zip(pts, pts[8:]):
        m = _mult_of((t1 - t0) / 8.0)
        if m and v1 > v0:
            ests.append((((t1 - t0) / (512.0 * m)) - (h1 - h0)) / (v1 - v0))
    return (int(round(median(ests))) if ests else 313), mults


def mult_at(mults, vbl):
    if not mults:
        return 1
    keys = [m[0] for m in mults]
    i = bisect.bisect_left(keys, vbl)
    cands = [mults[j] for j in (i - 1, i) if 0 <= j < len(mults)]
    return min(cands, key=lambda m: abs(m[0] - vbl))[1]


def parse(path):
    """-> (events, L, hz).  event = dict(kind cmd1|cmd2|force|complete, text, vbl, t seconds, pc, mult)."""
    raw = open(path, errors="replace").read().splitlines()
    L, mults = analyse_clock(raw)
    ev = []
    for ln in raw:
        if not ln.startswith("fdc "):
            continue
        body = ln[4:]
        if body.startswith("type IV force int"):
            kind = "force"
        elif body.startswith("complete command"):
            kind = "complete"
        elif body.startswith("type I "):
            kind = "cmd1"
        elif body.startswith("type II ") or body.startswith("type III "):
            kind = "cmd2"
        else:
            continue
        m = RE_VBL.search(ln)
        if not m:
            continue
        vbl = int(m.group(1))
        mult = mult_at(mults, vbl)
        mc, mh = RE_CYC.search(ln), RE_HBL.search(ln)
        if mc:
            cyc = int(mc.group(1)) / mult
        elif mh:
            cyc = int(mh.group(1)) * 512
        else:
            cyc = None
        t = None if cyc is None else (vbl * L * 512 + cyc) / CPS
        mp = RE_PC.search(ln)
        ev.append(dict(kind=kind, text=ln, vbl=vbl, t=t, pc=mp.group(1) if mp else None, mult=mult))
    return ev, L, CPS / (L * 512)


def type1_commands(ev):
    """Every type I command with how it ended ('complete' | 'FORCE-INT' | 'next-command' | 'eof') and its duration in s."""
    out = []
    for i, e in enumerate(ev):
        if e["kind"] != "cmd1":
            continue
        end = next((f for f in ev[i + 1:]), None)
        how = {"complete": "complete", "force": "FORCE-INT", "cmd1": "next-command", "cmd2": "next-command"}[end["kind"]] if end else "eof"
        dur = (end["t"] - e["t"]) if end and end["t"] is not None and e["t"] is not None else None
        out.append(dict(start=e, end=end, how=how, dur=dur))
    return out


def field(text, name):
    m = re.search(rf"{name}=(\S+)", text)
    return m.group(1) if m else None


def game_type1(ev):
    return [c for c in type1_commands(ev) if c["start"]["pc"] == GAME_PC]


def first_game_restore(ev):
    return next((c for c in game_type1(ev) if " restore " in c["start"]["text"]), None)


def summary_line(c):
    e = c["start"]
    d = "%.3f s" % c["dur"] if c["dur"] is not None else "?"
    return (f"{e['text'].split(' VBL=')[0]} | ends: {c['how']} after {d} (VBL {e['vbl']}"
            + (f" -> {c['end']['vbl']}" if c["end"] else "") + f", x{e['mult']} CPU)")


# ---- gate (a) verdict ------------------------------------------------------------------------------------------------------------------
TIMEOUT_STOCK_S = 2.176      # the game's `move.l #$50000,d0` wait on an 8 MHz machine (Hatari STE trace); halves at 16 MHz
TIMEOUT_V16_S = 2 * TIMEOUT_STOCK_S
MARGIN = 0.75                # the first restore must end within 75 % of the time-out in effect (stock v1.4 STE 8 MHz: 98 %)


def gate_first_restore(name, tracef, stock, log=print, cmds_path=None):
    """Gate (a).  PASS = the game's first restore starts parked (TR 0, head on track 0), completes (not cut by the game's force interrupt)
    within MARGIN x the time-out in effect, and NO game type I command in the whole trace was cut.  Returns (ok, details)."""
    ev, Lf, hz = parse(tracef)
    log(f'frame {Lf} lines = {hz:.1f} Hz')
    cmds = game_type1(ev)
    for c in cmds[:8]:
        log('  game type I: ' + summary_line(c))
    if cmds_path:
        open(cmds_path, 'w').write('\n'.join(summary_line(c) for c in cmds) + '\n')
    c = first_game_restore(ev)
    cuts = [x for x in cmds if x["how"] == "FORCE-INT"]
    if c is None:
        log(f'GATE first-restore {name}: NO game restore found')
        return False, {}
    e = c["start"]
    tr, head = field(e["text"], "tr"), field(e["text"], "head_track")
    teff = (TIMEOUT_STOCK_S if stock else TIMEOUT_V16_S) / e["mult"]
    dur = c["dur"] or 0.0
    parked = tr == "0x0" and head == "0x0"
    done = c["how"] == "complete"
    margin_ok = done and dur <= MARGIN * teff
    ok = parked and margin_ok and not cuts
    log(f'first game restore starts at tr={tr} head_track={head} ({"PARKED" if parked else "not parked"}); ends {c["how"]} after {dur:.3f} s'
        f' = {100 * dur / teff:.0f} % of the {teff:.2f} s time-out in effect ({"stock" if stock else "v1.6"} wait, CPU x{e["mult"]})')
    log(f'game type I commands cut by the force interrupt, whole run: {len(cuts)} of {len(cmds)}')
    for x in cuts[:5]:
        log('  CUT: ' + summary_line(x))
    log(f'GATE first-restore {name}: {"PASS" if ok else "FAIL"} (parked={parked} completed={done} margin<={int(MARGIN * 100)}%={margin_ok} cuts={len(cuts)})')
    return ok, dict(tr=tr, head=head, dur=dur, teff=teff, cuts=len(cuts))


if __name__ == "__main__":
    import sys
    a = sys.argv[1:]
    ok, _ = gate_first_restore(a[0], a[1], "--stock" in a)
    sys.exit(0 if ok else 1)
