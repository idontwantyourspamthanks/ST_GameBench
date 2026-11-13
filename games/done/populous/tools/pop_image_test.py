"""Populous from the all-games hard-disk image (ACSI + HDDRIVER, tools/make_hd_image.py): patient cold boot to play, then the patch marker, the tick hook
and the world rate.  The image path is slower than a GEMDOS drive (HDDRIVER, 200 KB HAGA chunk reads): tools/test_hd_image.py's fixed waits (about 58 s)
end before the game starts there and report `POPF` / turn garbage although nothing is wrong, so this one waits for the menu and for the hook.

    python3 tools/pop_image_test.py IMG MACHINE TOS MEM_KB [CPU_MHZ]        e.g. dist/AtariST_enhanced_games_*.img ste 1.62 1024
Prints one RESULT line: marker `POPP POPO` and hook `4ef9 000ba000` = patched and playing; `errors` lists the caught bus errors (PP's / HDDRIVER's hardware probes at boot).
"""
import sys, time, tempfile, shutil, re
from pathlib import Path
GP = Path(__file__).resolve().parent.parent
ROOT = GP.parent.parent.parent
sys.path[:0] = [str(ROOT / "tools"), str(GP / "tools")]
import test_hd_image as t
from populous import Populous, HOME, CONQUEST_XY, START_XY
from stharness import TOS


def rd(h, addr, n=4):
    """`m $addr n` of the debugger as hex bytes."""
    out = h.debug(f"m ${addr:x} {n}", 0.6)
    hx = re.findall(rf"{addr:08x}:\s+((?:[0-9a-f]{{2}} ?)+)", out, re.I)
    return hx[-1].strip() if hx else out.strip()


img = Path(sys.argv[1]); machine, tos, m = sys.argv[2], sys.argv[3], int(sys.argv[4]); cpu = int(sys.argv[5]) if len(sys.argv) > 5 else 0
R = Path(tempfile.mkdtemp(prefix="strun-"))
SRC = t.test_image(img, Path(tempfile.mkdtemp(prefix="hdsrc-")) / "test.img", "pop")
shutil.copy(SRC, R / "hd.img")
h = Populous(workdir=str(R), files=[], autorun="", extra=t.hd_args(R), machine=machine, tos=TOS[tos], memsize_kb=m)
BOX = (550, 360, 735, 455)
NUM = re.compile(r"#(\d+)(?:/-?\d+)? \(dec\)")


def sample_at(h, target):
    """VBL and the world turn word read at the same instant (a breakpoint on the VBL counter runs the debugger commands)."""
    f = h.R / f"smp{target}.txt"
    f.write_text("e VBL\ne ($3c506).w\ne CycleCounter\n")
    h.debug("b all", 0.3)
    s = len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {target} :trace :once :file {f}")
    t = time.time()
    while "Removed CPU breakpoint" not in h._logtext()[s:]:
        if time.time() - t > 300:
            raise TimeoutError("sample breakpoint never fired")
        time.sleep(0.3)
    time.sleep(0.4)
    vals = [int(m.group(1)) for m in NUM.finditer(h._logtext()[s:])]
    return {"VBL": vals[0], "T": vals[1], "CYC": vals[2]}
out = {}
try:
    t0 = time.time()
    t.wait_drive_c(h); time.sleep(10)
    h.key("space", 0.5)
    refp = GP / "work/ref/menu_buttons.png"
    out["menu"] = bool(h.wait_for(refp, BOX, timeout=400, poll=3))
    out["t_menu"] = round(time.time() - t0)
    h.goto(*CONQUEST_XY, home_xy=HOME); h.click(hold=0.4); time.sleep(12)
    play = False
    for k in range(8):
        h.goto(*START_XY, home_xy=HOME); h.click(hold=0.4)
        for _ in range(12):
            time.sleep(5)
            try:
                if rd(h, 0xB632, 6).replace(" ", "") == "4ef9000ba000":
                    play = True; break
            except Exception:
                pass
        if play: break
    out["hook"] = rd(h, 0xB632, 6)
    out["marker"] = rd(h, 0xB3000, 12)
    out["t_play"] = round(time.time() - t0)
    if play:
        if cpu:                       # HAGA's hardware screen resets the Mega STE speed register, so the clock is set once the game runs
            h.set_cpuclock(cpu)
            if machine == "megaste" and cpu >= 16:
                h.debug("w $ff8e21 $03", 0.5)
        time.sleep(8)
        time.sleep(2)
        h.cmd("hatari-option --fast-forward on")      # as work/scratch/poptick/cell.py: emulated time is what is measured
        s0 = sample_at(h, h.vbl() + 60); s1 = sample_at(h, s0["VBL"] + 1000)
        h.cmd("hatari-option --fast-forward off")
        hz = 50 if int(rd(h, 0xFF820A, 1).split()[0], 16) & 2 else 60       # TOS 2.06 (US) boots at 60 Hz
        out["Hz"] = hz
        out["turns/emulated s"] = round(((s1["T"] - s0["T"]) & 0xFFFF) / ((s1["VBL"] - s0["VBL"]) / hz), 3)
        out["cycles/VBL"] = round(((s1["CYC"] - s0["CYC"]) & 0xFFFFFFFF) / (s1["VBL"] - s0["VBL"]))
        out["$ff8e21"] = rd(h, 0xFF8E21, 1)
        out["ee16"] = rd(h, 0xEE16, 2)
    lg = h._logtext()
    out["errors"] = [l[:100] for l in lg.splitlines() if re.search("Bus Error|Address Error|double bus|halted", l)]
    h.shot(f"/tmp/imgfull_{machine}_{tos}_{m}.png")
finally:
    print("RESULT", machine, tos, m, out, flush=True)
    h.close()
