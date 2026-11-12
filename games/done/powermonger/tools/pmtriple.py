#!/usr/bin/env python3
"""Gates for the triple-buffer patches p7_triple_{wait,flip,tail} (notes: work/notes/triple.md).

    python3 tools/pmtriple.py trace SNAP MHZ VBLS [--orig | --nowait] [--pause]
                                                                  # no-tearing proof: video base / draw target / pointer buffer at every VBL and flip
                                                                  # (--orig: without p7, --nowait: negative control, --pause: poke the pause flag)
    python3 tools/pmtriple.py state SNAP MHZ VBLS [--selfcmp | --minus P ...]
                                                                  # RAM $0-$60000 at every loop top: defaults vs defaults + p7, per world tick
                                                                  # (--selfcmp / --minus: noise and timing-only controls without p7)
    python3 tools/pmtriple.py rate  SNAP MHZ VBLS [--hz 50|60] [--orig]      # world ticks per emulated second, defaults (+ p7)
    python3 tools/pmtriple.py fill  --disk D | --hd DIR [--acsi] [--machine M --tos T --mem K] [--query] [--saveload]
                                                                  # free-RAM proof of $6F30C-$77FFF (pattern loaded at the hand-over, compared after each stage)
    python3 tools/pmtriple.py boot  --disk D | --hd DIR [--acsi] [--machine M --tos T --mem K] [--scenario] [--query] [--saveload] [--mhz16] [--shots DIR]
                                                                  # cold boot of a build that contains p7: C changes, frames sane, flips rotate 3 buffers

`trace` and `state` apply live images at the first flip after the restore, as pmab.py does (snapshots hold unpatched code).
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path[:0] = [str(GAME.parent.parent.parent / "tools"), str(HERE)]
import pmab as AB  # noqa: E402
import pmtick as T  # noqa: E402
from pm import PM, SNAP  # noqa: E402

P7 = ["p7_triple_wait", "p7_triple_flip", "p7_triple_tail"]
QOL = ["qol_keys", "qol_keys2", "qol_hover", "qol_hover2"]
DEFAULTS = ["p4_ptr_a", "p4_ptr_b", "p4_spr", "p6_slope", "p6_tri", "p6_cpy", "p4_clamp", "pm_tooltip", "p3b_interp", "p3b_delta"]
BUFA, BUFB, BUFC = 0x1C700, 0x24400, 0x70000
PAT_LO, PAT_HI = 0x6F30C, 0x78000            # the proof range: after the FX.DAT / VBL counter words, up to the frame picture
SHOTS = GAME / "work" / "shots"
NAME = {BUFA: "A", BUFB: "B", BUFC: "C"}


def nm(a):
    return NAME.get(a, f"${a:x}")


# ---- trace: tearing proof ------------------------------------------------------------------------------------------
EV_V, EV_FE, EV_FX, EV_S1 = 0x1270, 0x187A, 0x13872, 0x13096   # VBL handler entry, flip entry, instruction after the main loop's `jsr flip`, after the loop-head wait (first draw: the window copy)
EXPR = ["VBL", "CycleCounter", "($ff8201).b", "($ff8203).b", "($2df78).l", "($2df7c).l"]


def trace_run(snap, mhz, names, vbls, walk=True, pokes=()):
    sp = AB.snap_path(snap)
    at = AB.at_vbl_for(sp)
    live = AB.make_live(names)
    h = AB.make_pm(snapshot=str(sp), memsize_kb=AB.memsize_of(sp))
    try:
        R = h.R
        time.sleep(1.0)
        if mhz != 8:
            h.set_cpuclock(mhz)
        cmds = AB.apply_cmds(live)
        cmds.append(f"w ${AB.PXADDR:x} $00 $e5 $00 $ad")
        if walk:
            cmds.append(f"w ${AB.MODE:x} $00 $01")
        cmds += list(pokes)
        for pc in (EV_V, EV_FE, EV_FX, EV_S1):
            (R / f"ev{pc:x}.txt").write_text("\n".join([f"e ${pc:x}"] + [f"e {e}" for e in EXPR]) + "\n")
            cmds.append(f"b pc = ${pc:x} :trace :file {R / f'ev{pc:x}.txt'}")
        flag = R / "end.flag"
        end = R / "end.txt"
        end.write_text(f"b all\nsavebin {flag} $0 2\ne VBL\n")
        cmds.append(f"b VBL > {at + vbls} :trace :once :file {end}")
        app = R / "apply.txt"
        app.write_text("\n".join(cmds) + "\n")
        start = len(h._logtext())
        h.cmd(f"hatari-debug b VBL > {at} && pc = ${AB.APPLYPC:x} :trace :once :file {app}")
        time.sleep(0.3)
        h.cmd("hatari-option --fast-forward on")
        t = time.time()
        while not flag.exists():
            if time.time() - t > 900:
                raise TimeoutError("trace run did not finish")
            time.sleep(0.5)
        time.sleep(1.0)
        text = h._logtext()[start:]
    finally:
        h.close()
    ev = []
    for blk in text.split("CPU breakpoint condition(s) matched")[1:]:
        m = [int(v) for v in AB.NUM.findall(blk)]
        if len(m) >= 7 and m[0] in (EV_V, EV_FE, EV_FX, EV_S1):
            pc, vbl, cyc, b1, b2, l, d = m[:7]
            ev.append(dict(pc=pc, vbl=vbl, cyc=cyc, base=(b1 << 16) | (b2 << 8), L=l, D=d))
    return ev


def analyse(ev, label):
    """Drawing into D starts at EV_S1 (the window copy, right after the loop-head wait) and ends at EV_FE (the flip).  Over that interval the buffer
    that is scanned (the base register as latched at the last VBL) and the one the pointer lives in ([$2df78] at the last VBL, the VBL handler
    restores and redraws it there) must both differ from D, at the start, at every VBL inside it and at its end."""
    S = PTR = None
    drawing, D = False, None
    nint = nvbl = viol = nflip = 0
    viol_list = []
    last_fe_vbl = None
    spacing, to_vbl, to_s1 = [], [], []
    fx_cyc = fx_v = None
    seen = {}

    def check(where, vbl):
        nonlocal viol
        for what, v in (("scanned", S), ("pointer", PTR)):
            if v is not None and v == D:
                viol += 1
                viol_list.append(f"{where} (VBL {vbl}): drawing into {nm(D)} while the {what} buffer is {nm(v)}")

    for e in ev:
        if e["pc"] == EV_V:
            S, PTR = e["base"], e["L"]
            if fx_v is not None:
                to_vbl.append((e["cyc"] - fx_v) & 0xFFFFFFFF)
                fx_v = None
            if drawing:
                nvbl += 1
                check("VBL inside the draw interval", e["vbl"])
        elif e["pc"] == EV_S1:
            D = e["D"]
            drawing = True
            if fx_cyc is not None:
                to_s1.append((e["cyc"] - fx_cyc) & 0xFFFFFFFF)
                fx_cyc = None
            check("draw start", e["vbl"])
        elif e["pc"] == EV_FE:
            nflip += 1
            if drawing:
                nint += 1
                check("flip entry", e["vbl"])
            if last_fe_vbl is not None:
                spacing.append(e["vbl"] - last_fe_vbl)
            last_fe_vbl = e["vbl"]
            seen[(e["L"], e["D"])] = seen.get((e["L"], e["D"]), 0) + 1
            drawing = False
        elif e["pc"] == EV_FX:
            fx_cyc = fx_v = e["cyc"]
    print(f"{label}: events {len(ev)} (VBL {sum(1 for e in ev if e['pc'] == EV_V)}, flips {nflip}), draw intervals checked {nint}, "
          f"VBLs inside a draw interval checked {nvbl}: VIOLATIONS {viol}")
    print("  (L, D) pairs at flip entry: " + ", ".join(f"({nm(l)},{nm(d)}) x{n}" for (l, d), n in sorted(seen.items())))
    if spacing:
        print(f"  VBLs between consecutive flips: min {min(spacing)} max {max(spacing)} mean {sum(spacing) / len(spacing):.2f} "
              f"(0 would mean a flipped frame replaced one that was never shown)")
    if to_s1:
        print(f"  cycles from a flip's return to the first draw (loop-head wait + logic stage): mean {sum(to_s1) / len(to_s1):.0f} over {len(to_s1)} passes")
    if to_vbl:
        print(f"  cycles from a flip's return to the next VBL: mean {sum(to_vbl) / len(to_vbl):.0f} over {len(to_vbl)} flips")
    for v in viol_list[:10]:
        print("  VIOLATION", v)
    return viol, spacing


def cmd_trace(a):
    names = AB.TICK + AB.TESTSET + DEFAULTS + (["test_nowait"] if a.nowait else [] if a.orig else P7 + (QOL if a.qol else []))
    ev = trace_run(a.snap, a.mhz, names, a.vbls, pokes=["w $57ff2 $00 $01"] if a.pause else [])
    v, sp = analyse(ev, f"{a.snap} {a.mhz} MHz {'PAUSED ' if a.pause else ''}{'NEGATIVE CONTROL: double buffer, loop-head wait removed' if a.nowait else 'ORIGINAL double buffer' if a.orig else 'p7 triple buffer'}")
    ok = v == 0 and (not sp or min(sp) >= 1)
    print("NO TEARING" if ok else "TEARING / REUSE VIOLATION")
    return 0 if ok != a.nowait else 1          # the negative control passes when the checker reports a violation


# ---- state: RAM equality per world tick ----------------------------------------------------------------------------
T.SITE_MASKS += [(0x13090, 0x13096), (0x1386C, 0x13872), (0x1898, 0x18A0), (0x12138, 0x1213E), (0x130B6, 0x130BC), (0x130FC, 0x13102), (0x199C, 0x199C + 6)]   # + the qol sites
# the game's key table: host key events reach the ACIA handler at a time that depends on the pass timing.  `state --minus p6_cpy` (defaults against
# defaults minus a patch that only changes the pass length) shows the same differences at $2de6c-$2dea8 without p7 involved; `--selfcmp` shows none.
T.MASKS.append((0x2DE6C, 0x2DEA8, "key table (input timing)"))


def cmd_state(a):
    base = AB.TICK + AB.TESTSET + DEFAULTS       # test_walk*: the pointer is a function of the tick (see below)
    lb = AB.make_live(base)
    if a.selfcmp:
        lp = lb                                              # noise control: defaults against defaults
    elif a.minus:
        lp = AB.make_live([n for n in base if n not in a.minus])   # timing-only control: defaults against defaults without e.g. p6_cpy (pixel- and state-neutral, different pass lengths)
    else:
        lp = AB.make_live(base + P7 + (QOL if a.qol else []))
    res = {}

    def one(name, live):
        for attempt in range(3):          # the debugger's answers can come late on a loaded host (IndexError in h.vbl())
            h = PM(snapshot=str(SNAP / f"{a.snap}.sav"))
            try:
                time.sleep(1.5)
                res[name] = T.log_passes(h, live, a.mhz, a.vbls, name, [f"w ${AB.PXADDR:x} $00 $e5 $00 $ad", f"w ${AB.MODE:x} $00 $01"])
                return
            except Exception as e:  # noqa: BLE001
                print(f"  {name}: attempt {attempt + 1} failed: {e!r}", flush=True)
            finally:
                h.close()
    ts = [threading.Thread(target=one, args=("U", lb)), threading.Thread(target=one, args=("P", lp))]
    [t.start() for t in ts]
    [t.join() for t in ts]
    U, P = res["U"], res["P"]
    ubl, ub = {}, {}
    for it, k, b in U:
        ubl.setdefault(k, []).append(b)
        ub.setdefault(k, b)
    its = [it for it, _, _ in P]
    print(f"{a.snap} {a.mhz} MHz: defaults {len(U)} loop tops (ticks {U[0][1]}..{U[-1][1]}), defaults + p7 {len(P)} loop tops (ticks {P[0][1]}..{P[-1][1]}), "
          f"missed loop tops {sum(max(0, y - x - 1) for x, y in zip(its, its[1:]))}")
    bad, n, ticks, vals = {}, 0, set(), {}
    for it, k, b in P:
        u = ub.get(k)          # state outside the masks is a function of the world tick (R passes change none of it): compare with the first top of the tick
        if u is None:
            continue
        n += 1
        ticks.add(k)
        for g in T.group(T.diff_words(u, b)):
            bad.setdefault((g[0], g[1]), []).append(it)
            if len(vals.setdefault((g[0], g[1]), [])) < 6:
                vals[(g[0], g[1])].append((it, k, u[g[0]:g[1]].hex(), b[g[0]:g[1]].hex()))
    print(f"compared {n} loop tops over {len(ticks)} distinct world ticks (RAM $0-$60000, masks as pmtick.py MASKS + the three p7 sites)")
    neg = sum(1 for it, k, b in P if ub.get(k + 1) is not None and T.diff_words(ub[k + 1], b))
    nn = sum(1 for it, k, b in P if ub.get(k + 1) is not None)
    print(f"negative control: p7 tick k vs defaults tick k+1 differs in {neg} of {nn} loop tops")
    rng = sum(1 for it, k, b in P if ub.get(k) is not None and ub[k][0x2DF84:0x2DF88] != b[0x2DF84:0x2DF88])
    print(f"RNG $2df84 differs in {rng} loop tops; {len(set(b[0x2DF84:0x2DF88] for _, _, b in P))} distinct values")
    mv = sum(1 for i in range(512) if P[0][2][0x51B66 + i * 50 + 8:0x51B66 + i * 50 + 12] != P[-1][2][0x51B66 + i * 50 + 8:0x51B66 + i * 50 + 12])
    print(f"men records whose x/z changed first -> last loop top: {mv}")
    if not bad:
        print("IDENTICAL")
    else:
        for (lo, hi), its in sorted(bad.items())[:40]:
            print(f"DIFF ${lo:x}-${hi:x} in {len(its)} loop tops, first iters {its[:4]}")
            for v in vals[(lo, hi)]:
                print("    iter %d tick %d defaults %s p7 %s" % v)
    return 0 if not bad else 1


# ---- fill / boot: cold boots --------------------------------------------------------------------------------------
def fill_byte(a):
    return 1 + ((a * 167 + (a >> 8) * 53) % 251)


def report(name, d):
    bad = [a for a in range(PAT_LO, PAT_HI) if d[a] != fill_byte(a)]
    runs = []
    for a in bad:
        if runs and a - runs[-1][1] <= 1:
            runs[-1][1] = a
        else:
            runs.append([a, a])
    if bad:
        Path(f"/tmp/pt/changed_{name.replace(' ', '_')}.bin").write_bytes(d[PAT_LO:PAT_HI])
    print(f"  fill[{name}]: {PAT_HI - PAT_LO} pattern bytes in ${PAT_LO:x}..${PAT_HI - 1:x}, {len(bad)} changed"
          + (f", runs {[(hex(x), hex(y)) for x, y in runs[:8]]}" if bad else ""), flush=True)
    return not bad


def open_query(h):
    """Query icon, then a click on the village house: the window with the house name opens over the 3D view (pminterp.py ui)."""
    h.click_st(76, 191, wait=1.5)
    h.click_st(178, 103, wait=1.5)


def make_pm(disk, hd, acsi, machine, tos, mem):
    import pm
    import pmpatch as PP
    return PP.make_pm(disk, hd, acsi=acsi, machine=machine, tos=pm.TOS[tos], memsize_kb=mem), PP


def saveload_split(h, PP, acsi, tag="pattern"):
    """pmpatch.run_saveload's two halves (the game's own Option -> FILE -> SAVE, then LOAD, slot A, HD builds: hd_sector at $bb00c), with the
    free-RAM report after each half instead of one at the end."""
    out = h.R / "sl"
    out.mkdir(exist_ok=True)
    lo, n = PP.STATE
    for f in out.glob("*.bin"):
        f.unlink()
    ok = True
    (h.R / "sv.txt").write_text(f"savebin {out}/save.bin ${lo:x} ${n:x}\n")
    if not PP.file_dialog(h, "pm_btn_save.png", lambda: h.cmd(f"hatari-debug b pc = $bb00c && d3 = $8001 && d2 = $c6 :trace :once :file {h.R / 'sv.txt'}")):
        print("  saveload: FILE / SAVE buttons not found")
        return False
    t, n_ok = time.time(), 0
    while not (out / "save.bin").exists() or (out / "save.bin").stat().st_size < n:
        if time.time() - t > 90:
            print("  saveload: the save never reached hd_sector")
            return False
        time.sleep(1)
        p = PP.find_btn(h, "pm_btn_ok.png", quiet=True)
        if p is not None and n_ok < 3:
            n_ok += 1
            h.click_st(*p, wait=1.0)
    time.sleep(8)
    print(f"  save done: in_game={h.in_game()} iter {h.iter_count()}", flush=True)
    ok &= report("after save", h.ram(0, 0x100000)) if tag == "pattern" else True
    (h.R / "l2.txt").write_text(f"savebin {out}/load.bin ${lo:x} ${n:x}\n")
    (h.R / "l1.txt").write_text(f"b pc = $1bdd8 :trace :once :file {h.R / 'l2.txt'}\n")
    if not PP.file_dialog(h, "pm_btn_load.png", lambda: h.cmd(f"hatari-debug b pc = $bb00c && d3 = $8000 && d2 = $c6 :trace :once :file {h.R / 'l1.txt'}")):
        print("  saveload: FILE / LOAD buttons not found")
        return False
    t = time.time()
    while not (out / "load.bin").exists() or (out / "load.bin").stat().st_size < n:
        if time.time() - t > 90:
            print("  saveload: the load never returned")
            break
        time.sleep(1)
    time.sleep(5)
    print(f"  load done: in_game={h.in_game()} iter {h.iter_count()}", flush=True)
    ok &= report("after load", h.ram(0, 0x100000)) if tag == "pattern" else True
    sv, ld = ((out / f"{k}.bin").read_bytes() if (out / f"{k}.bin").exists() else b"" for k in ("save", "load"))
    print(f"  saved vs loaded state: {sum(x != y for x, y in zip(sv, ld))} bytes differ ({len(sv)}/{len(ld)} B)")
    return ok


def cmd_fill(a):
    h, PP = make_pm(Path(a.disk) if a.disk else None, Path(a.hd) if a.hd else None, a.acsi, a.machine, a.tos, a.mem)
    try:
        f = h.R / "pat.bin"
        f.write_bytes(bytes(fill_byte(x) for x in range(PAT_LO, PAT_HI)))
        (h.R / "fill.txt").write_text(f"loadbin {f} ${PAT_LO:x}\n")
        base, first, what = (PP.BASE2, 0x41F9, "stage 2") if a.hd else (PP.BASE1, 0x4EB9, "stage 1")
        h.cmd(f"hatari-debug b pc = ${base:x} && (${base:x}).w = ${first:x} :trace :once :file {h.R / 'fill.txt'}")
        print(f"fill armed at the {what} hand-over: {PAT_HI - PAT_LO} bytes", flush=True)
        h.boot_to_game()
        print(f"BOOT OK {a.machine} {a.tos} {a.mem}K in_game={h.in_game()} marker={h.peekl(PP.MARKER).to_bytes(4, 'big')!r}", flush=True)
        ok = report("map view", h.ram(0, 0x100000))
        n = h.scenario_get_men()
        print(f"  get_men: {n} people moving")
        ok &= report("get_men", h.ram(0, 0x100000))
        if a.query:
            open_query(h)
            SHOTS.mkdir(parents=True, exist_ok=True)
            h.shot(str(SHOTS / "triple_fill_query.png"))
            time.sleep(3)
            ok &= report("query window", h.ram(0, 0x100000))
        t = time.time()
        while h.iter_count() < 340 and time.time() - t < 240:
            time.sleep(5)
        print(f"  battle: iteration {h.iter_count()}")
        ok &= report("battle", h.ram(0, 0x100000))
        if a.saveload:
            ok &= saveload_split(h, PP, a.acsi)
            time.sleep(10)
            ok &= report("after save + load + 10 s", h.ram(0, 0x100000))
        print("FREE" if ok else "NOT FREE")
        return 0 if ok else 2
    finally:
        h.close()


def sample_lds(h, secs=6.0):
    """(L, D) = ([$2df78], [$2df7c]) at the entry of every flip during `secs` seconds, read by ONE debugger stop per flip (`e` at pc = $187a)
    and parsed from the log (peekl twice is two stops and can mix an answer of the previous command into the next one)."""
    f = h.R / "lds.txt"
    f.write_text(f"e ${EV_FE:x}\ne ($2df78).l\ne ($2df7c).l\n")
    h.debug("b all", 0.3)
    s0 = len(h._logtext())
    h.cmd(f"hatari-debug b pc = ${EV_FE:x} :trace :file {f}")
    time.sleep(secs)
    h.debug("b all", 0.5)
    seen = {}
    for blk in h._logtext()[s0:].split("CPU breakpoint condition(s) matched")[1:]:
        m = [int(v) for v in AB.NUM.findall(blk)]
        if len(m) >= 3 and m[0] == EV_FE:
            seen[(m[1], m[2])] = seen.get((m[1], m[2]), 0) + 1
    return {f"({nm(l)},{nm(d)})": c for (l, d), c in sorted(seen.items())}


def tstate(h, PP):
    return f"IN={h.peekw(0xDB000)} OURS={h.peekw(0xDB002)}"


def cmd_boot(a):
    """Cold boot of a build that contains p7: map view, then (--scenario) get men, (--query) the query window, (--saveload) the game's own
    FILE / SAVE / LOAD menus (modal loops with plain flips, then back to the three-buffer loop), a screenshot after each; the three-buffer
    state (L, D) and the data block T are sampled after each step."""
    h, PP = make_pm(Path(a.disk) if a.disk else None, Path(a.hd) if a.hd else None, a.acsi, a.machine, a.tos, a.mem)
    shots = Path(a.shots) if a.shots else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    tag = f"{a.machine}_{a.tos}_{a.mem}{'_hd' if a.hd else ''}{'_acsi' if a.acsi else ''}"

    def shot(what):
        if shots:
            h.shot(str(shots / f"triple_{tag}_{what}.png"))

    ok = True
    try:
        t0 = time.time()
        h.boot_to_game()
        print(f"BOOT OK {tag} after {time.time() - t0:.0f} s in_game={h.in_game()} marker={h.peekl(PP.MARKER).to_bytes(4, 'big')!r} flags={h.peekl(PP.FLAGS):#x}", flush=True)
        print("  sites:", {hex(s): h.ram(s, 6).hex() for s in (0x13090, 0x1386C, 0x1898)})
        shot("map")
        print("  map view: (L, D) samples", sample_lds(h), tstate(h, PP), flush=True)
        if a.scenario:
            print(f"  get_men: {h.scenario_get_men()} people moving")
            shot("getmen")
            print("  get_men: (L, D) samples", sample_lds(h, secs=5), tstate(h, PP), flush=True)
        if a.query:
            open_query(h)
            time.sleep(2)
            shot("query")
            print("  query window: (L, D) samples", sample_lds(h, secs=5), tstate(h, PP), f"iter {h.iter_count()}", flush=True)
        if a.saveload:
            ok &= PP.run_saveload(h, a.acsi)
            time.sleep(3)
            shot("after_saveload")
            print("  after save + load: (L, D) samples", sample_lds(h, secs=5), tstate(h, PP), f"iter {h.iter_count()} in_game={h.in_game()}", flush=True)
        c = h.ram(BUFC, 32000)
        print(f"  C ${BUFC:x}: {sum(1 for b in c if b)} non-zero bytes of 32000")
        if a.mhz16:
            h.set_cpuclock(16)
            time.sleep(1)
            v0, i0 = h.vbl(), h.iter_count()
            time.sleep(10)
            print(f"  16 MHz: passes {h.iter_count() - i0} in {h.vbl() - v0} VBL, in_game={h.in_game()}", flush=True)
            shot("16mhz")
        ok &= h.in_game()
        print("COLD BOOT OK" if ok else "COLD BOOT PROBLEM")
        return 0 if ok else 1
    finally:
        h.close()


# ---- rate: world ticks per emulated second ---------------------------------------------------------------------------
def cmd_rate(a):
    """pmtick.py rate with the defaults (+ p7 unless --orig): ticks `$4bb3e` and passes (`$2df70`) per EMULATED second between two atomic samples
    (`e VBL`, `e CycleCounter` at one debugger stop each), at 50 or 60 Hz (--hz 60 pokes $ff820a at the flip)."""
    names = AB.TICK + AB.TESTSET + DEFAULTS + ([] if a.orig else P7)
    live = AB.make_live(names)
    h = PM(snapshot=str(SNAP / f"{a.snap}.sav"))
    try:
        time.sleep(1.5)
        if a.mhz != 8:
            h.set_cpuclock(a.mhz)
        T.at_flip(h, AB.apply_cmds(live) + [f"w ${AB.PXADDR:x} $00 $e5 $00 $ad", f"w ${AB.MODE:x} $00 $01"] + (["w $ff820a $00"] if a.hz == 60 else []))
        time.sleep(1.0)
        ex = ["VBL", "CycleCounter", f"(${T.TICKCNT:x}).l", f"(${T.ITER:x}).l"]
        s0 = T.sample_at(h, h.vbl() + 40, ex)
        s1 = T.sample_at(h, s0["VBL"] + a.vbls, ex)
        dv = s1["VBL"] - s0["VBL"]
        secs = dv / a.hz
        t, it = s1[ex[2]] - s0[ex[2]], s1[ex[3]] - s0[ex[3]]
        print(f"RATE {a.snap} {a.mhz} MHz {a.hz} Hz {'defaults' if a.orig else 'defaults + p7'}: {dv} VBL = {secs:.2f} s, "
              f"{((s1['CycleCounter'] - s0['CycleCounter']) & 0xFFFFFFFF) / dv:.0f} cycles/VBL, world ticks {t} = {t / secs:.3f}/s, $2df70 steps {it} = {it / secs:.3f}/s")
    finally:
        h.close()
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("rate")
    r.add_argument("snap")
    r.add_argument("mhz", type=int)
    r.add_argument("vbls", type=int)
    r.add_argument("--hz", type=int, choices=[50, 60], default=50)
    r.add_argument("--orig", action="store_true", help="without p7")
    for n in ("trace", "state"):
        p = sub.add_parser(n)
        p.add_argument("snap")
        p.add_argument("mhz", type=int)
        p.add_argument("vbls", type=int)
        p.add_argument("--selfcmp", action="store_true", help="state: noise control (defaults against defaults, no p7 on either side)")
        p.add_argument("--minus", nargs="*", default=[], help="state: control = defaults against defaults MINUS these patches (a timing difference without p7)")
        p.add_argument("--qol", action="store_true", help="state / trace: the patched side also carries qol_keys qol_keys2 qol_hover qol_hover2 (the combined default set)")
        p.add_argument("--orig", action="store_true", help="trace: the default set WITHOUT p7 (the original double buffer) instead")
        p.add_argument("--pause", action="store_true", help="trace: poke the game's pause flag $57ff2 at the apply flip (passes without the landscape: shorter than a VBL, the flip wait is the only pacing)")
        p.add_argument("--nowait", action="store_true", help="trace: negative control = double buffer with the loop-head VBL wait removed (test_nowait)")
    for n in ("fill", "boot"):
        p = sub.add_parser(n)
        p.add_argument("--disk")
        p.add_argument("--hd")
        p.add_argument("--acsi", action="store_true")
        p.add_argument("--machine", default="ste")
        p.add_argument("--tos", default="1.62")
        p.add_argument("--mem", type=int, default=1024)
        p.add_argument("--query", action="store_true")
        p.add_argument("--saveload", action="store_true")
        p.add_argument("--scenario", action="store_true")
        p.add_argument("--mhz16", action="store_true", help="boot: also run 10 s at 16 MHz")
        p.add_argument("--shots")
    a = ap.parse_args()
    sys.exit({"trace": cmd_trace, "state": cmd_state, "fill": cmd_fill, "boot": cmd_boot, "rate": cmd_rate}[a.cmd](a))


if __name__ == "__main__":
    main()
