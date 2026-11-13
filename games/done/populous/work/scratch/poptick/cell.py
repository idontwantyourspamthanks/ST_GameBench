"""PopTiming cold-boot cell (test scaffolding only; uses the PopMachines scratch helpers for TT / Falcon navigation).

    python3 cell.py CELL MEDIUM PATH [--clocks 8 16] [--hz 50 60] [--vbls 1500] [--tag NAME] [--mem KB] [--tos V]

CELL = ste | megaste | tt | falcon   MEDIUM = gemdos (HD build dir) | floppy (Populous_boot.st)
Boots to play, finds D (the text-base delta, payload RELDLT at $B3104), then for every (hz, clock): turns per emulated second over --vbls VBL.
"""
import argparse, re, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
MACH_DIR = HERE.parent / "machines"
GAME = HERE.parents[2]
sys.path[:0] = [str(MACH_DIR), str(GAME / "tools"), str(GAME.parent.parent.parent / "tools")]
import pm_cells as pc            # noqa: E402
from mm import start, mem        # noqa: E402
from populous import HOME, CONQUEST_XY, START_XY   # noqa: E402

TURN = 0x3C506
BOX = (550, 360, 735, 455)       # the TUTORIAL / CONQUEST / CUSTOM buttons of the menu, ST screenshot coordinates
D_ = 0xBb000
oRON, oTICKS, oRPASS, oSPASS, oPPASS, oTPASS = 16, 28, 32, 36, 40, 44
NUM = re.compile(r"#(\d+)(?:/-?\d+)? \(dec\)")
HEX = re.compile(r"\$([0-9a-fA-F]+) \(hex\)")


def wait_gone(h, start_, timeout=900):
    t = time.time()
    while "Removed CPU breakpoint" not in h._logtext()[start_:]:
        if time.time() - t > timeout:
            raise TimeoutError("breakpoint never fired")
        time.sleep(0.3)
    time.sleep(0.4)


def sample_at(h, target, exprs):
    f = h.R / f"smp{target}.txt"
    f.write_text("".join(f"e {e}\n" for e in exprs))
    h.debug("b all", 0.3)
    s = len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {target} :trace :once :file {f}")
    wait_gone(h, s)
    out = {}
    for m in re.finditer(r"> e (.+)\n(?:  .*\n)*= (.*)", h._logtext()[s:]):
        out[m.group(1)] = int(HEX.search(m.group(2)).group(1), 16)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cell"); ap.add_argument("medium"); ap.add_argument("path")
    ap.add_argument("--clocks", type=int, nargs="*", default=[0])
    ap.add_argument("--hz", type=int, nargs="*", default=[])
    ap.add_argument("--vbls", type=int, default=1500)
    ap.add_argument("--tag", default="cell")
    ap.add_argument("--mem", type=int); ap.add_argument("--tos")
    ap.add_argument("--extra", default="")
    ap.add_argument("--nomenu", action="store_true"); ap.add_argument("--boot-wait", type=int, default=16)
    a = ap.parse_args()
    pc.NOMENU = a.nomenu
    shots = GAME / "work" / "shots"
    h = start(a.cell, a.medium, a.path, extra=a.extra.split(), mem=a.mem, tos=a.tos)
    try:
        if a.cell in ("tt", "falcon") and a.nomenu:
            time.sleep(70)
        elif a.cell in ("tt", "falcon"):
            if a.medium == "gemdos" and a.cell == "falcon":
                time.sleep(a.boot_wait)
                h.key("space", 0.5)                     # PP's hardware screen (HD build)
            r = pc.to_start_page(h, a.cell, None)
            if not r:
                print("START page not reached:", r)
                return 1
            pc.goto_shot(h, a.cell, "game", *pc.START_B)
            h.click(hold=0.4)
        else:
            from PIL import Image
            refp = HERE / "menu_buttons_ref.png"
            if not refp.exists():                       # a crop of the menu of an earlier cold boot (git-ignored shots dir)
                Image.open(GAME / "work" / "shots" / "boot_megaste16_menu.png").convert("RGB").crop(BOX).save(refp)
            time.sleep(a.boot_wait)
            h.key("space", 0.5)                         # PP's hardware screen
            if a.medium == "floppy":
                time.sleep(80)                          # the credits roll while the disk loads; a key skips them
                h.key("space", 0.5)
            ok = h.wait_for(refp, BOX, timeout=240, poll=2)     # the menu is up for ~10 s, then the credits come back
            print("menu seen:", ok, flush=True)
            h.shot(str(shots / f"tick_{a.tag}_menu.png"))
            h.goto(*CONQUEST_XY, home_xy=HOME)
            h.click(hold=0.4)
            time.sleep(40 if a.medium == "floppy" else 9)
            h.goto(*START_XY, home_xy=HOME)
            h.click(hold=0.4)
        time.sleep(12)
        D = pc.delta(h)
        print("payload header:", mem(h, 0xB3000, 16), " D =", D, "core2:", mem(h, 0xB3E00, 32))
        if D is None:
            print("no payload"); return 2
        t1 = h.peekw(TURN + D); time.sleep(2.0); t2 = h.peekw(TURN + D)
        sig = mem(h, 0xB632 + D, 6).replace(" ", "")
        print(f"turn {t1} -> {t2}; $b632 {sig}; tick marker {mem(h, D_, 4)}")
        h.shot(str(shots / f"tick_{a.tag}.png"))
        ex = ["VBL", "CycleCounter", f"(${TURN + D:x}).w"] + [f"(${D_ + o:x}).l" for o in (oTICKS, oTPASS, oRPASS, oSPASS, oPPASS)]
        sync = int(mem(h, 0xFF820A, 1).split()[0], 16)
        print(f"$ff820a = ${sync:02x} -> {50 if sync & 2 else 60} Hz")
        for hz in (a.hz or [50 if sync & 2 else 60]):
            cur = 50 if int(mem(h, 0xFF820A, 1).split()[0], 16) & 2 else 60
            if hz != cur:
                h.debug("w $ff820a $%02x" % (2 if hz == 50 else 0), 0.5)
                time.sleep(1.0)
            for mhz in a.clocks:
                if mhz:
                    h.set_cpuclock(mhz)
                    if a.cell == "megaste":
                        h.debug("w $ff8e21 $%02x" % (3 if mhz >= 16 else 0), 0.5)
                time.sleep(1.0)
                h.cmd("hatari-option --fast-forward on")
                s0 = sample_at(h, h.vbl() + 60, ex)
                s1 = sample_at(h, s0["VBL"] + a.vbls * hz // 50, ex)
                h.cmd("hatari-option --fast-forward off")
                dv = s1["VBL"] - s0["VBL"]; secs = dv / hz
                cyc = ((s1["CycleCounter"] - s0["CycleCounter"]) & 0xFFFFFFFF) / dv
                cpu = mhz or {"st": 8, "ste": 8, "megaste": 8, "tt": 32, "falcon": 16}[a.cell]
                seen = cpu * 1e6 / cyc
                turns = (s1[ex[2]] - s0[ex[2]]) & 0xFFFF
                k = [s1[e] - s0[e] for e in ex[3:]]
                print(f"RESULT cold {a.cell} {a.medium} {Path(a.path).name} {mhz or 'default'} MHz {hz} Hz: {dv} VBL = {secs:.2f} s, {cyc:.0f} cycles/VBL (refresh seen {seen:.2f} Hz"
                      + ("" if abs(seen - hz) < 0.03 * hz else f" *** NOT {hz} Hz ***") + f"), world turns {turns} = {turns / secs:.3f}/s | ticks {k[0]} = {k[0] / secs:.3f}/s; passes T {k[1]} R {k[2]} S {k[3]} P {k[4]}", flush=True)
        h.shot(str(shots / f"tick_{a.tag}_end.png"))
    finally:
        lg = h._logtext()
        print("ERRORS", {k: len(re.findall(k, lg)) for k in ("Bus Error", "Address Error", "double bus", "CPU halted")}, "log", h.logpath, flush=True)
        for ln in lg.splitlines():
            if re.search("Bus Error|Address Error|double bus|CPU halted", ln):
                print("  ERRLINE", ln[:160], flush=True)
        h.close()


if __name__ == "__main__":
    sys.exit(main() or 0)
