import sys, time, pathlib
sys.path.insert(0, "tools")
from stharness import Hatari

ROOT = pathlib.Path("games/in_progress/player-manager")
WORK = ROOT / "work"

def measure_ko2_patched():
    """Measure Patched PM + KO2 match engine on 1MB 8MHz STE (50fps fix, -$34c4=0)."""
    h = Hatari(game_dir=str(ROOT / "build/game"),
               snapshot=str(WORK / "t2_ko2_LAUNCHED.sav"), machine="ste", memsize_kb=1024)
    try:
        h.debug(f"loadbin {WORK}/micro_opt.bin $b3000", wait=0.2)
        h.click()
        time.sleep(10.0)
        a4 = 0x284aa
        # Enable Watch mode so both teams play actively across the pitch
        h.debug(f"w ${a4-0x4ef0:x} $00 $01", wait=0.05)
        time.sleep(2.5)
        # Measure 50 FPS mode (-$4ed6 = 0)
        v0, f0 = h.peekl(0x462), h.peekl(a4 - 0x4f4e)
        cam_samples = []
        for i in range(6):
            time.sleep(0.5)
            cam_samples.append((h.peekw(0x2739c), h.peekw(0x27188) >> 8))
        v1, f1 = h.peekl(0x462), h.peekl(a4 - 0x4f4e)
        fps_50 = (f1 - f0) / max(1, (v1 - v0)) * 50.0
        # Also measure old buggy -$4ed6 = 1 mode for before/after comparison!
        h.debug(f"w ${a4-0x4ed6:x} $00 $01", wait=0.05)
        time.sleep(0.2)
        v2, f2 = h.peekl(0x462), h.peekl(a4 - 0x4f4e)
        time.sleep(2.5)
        v3, f3 = h.peekl(0x462), h.peekl(a4 - 0x4f4e)
        fps_25 = (f3 - f2) / max(1, (v3 - v2)) * 50.0
        # Also sample how much of a 50Hz frame KO2 spends waiting in VBL wait ($1b4b2..$1b4b6)
        h.debug(f"w ${a4-0x4ed6:x} $00 $00", wait=0.05)
        time.sleep(0.2)
        idle_hits = 0
        N = 40
        for _ in range(N):
            r = h.debug("r", wait=0.04)
            if "0001b4b2" in r or "0001b4b6" in r:
                idle_hits += 1
            time.sleep(0.03)
        return {
            "fps_fixed": fps_50,
            "vbl_fixed": v1 - v0,
            "frm_fixed": f1 - f0,
            "fps_before_fix": fps_25,
            "vbl_before_fix": v3 - v2,
            "frm_before_fix": f3 - f2,
            "idle_pct": idle_hits * 100.0 / N,
            "cam_samples": cam_samples,
        }
    finally:
        h.close()

def measure_unpatched_pm():
    """Cold-boot Unpatched originals/PLAYERME -> Demo Game -> Match day -> Play Match."""
    h = Hatari(game_dir=str(ROOT / "originals/PLAYERME"),
               snapshot=None, machine="ste", memsize_kb=1024)
    try:
        for _ in range(4):
            time.sleep(2.5)
            h.keypress(57)
        time.sleep(2.0)
        # Title -> Load Game -> Cancel -> Credits -> Main Menu -> Demo Game
        h.click(); time.sleep(2.0)
        h.rel(150, 120); time.sleep(0.3); h.click(); time.sleep(2.0)
        h.click(); time.sleep(2.0)
        # Main Menu -> Demo Game (bottom button: rel(-150, -20))
        h.rel(-150, -20); time.sleep(0.3)
        h.shot(str(WORK / "unpatched_menu.png"))
        h.click(); time.sleep(3.5)
        h.shot(str(WORK / "unpatched_demo.png"))
        # Move to Match day (center-bottom) and click
        h.rel(0, 30); time.sleep(0.2); h.click(); time.sleep(2.0)
        h.shot(str(WORK / "unpatched_matchday.png"))
        h.savemem(str(WORK / "unpatched_matchday.sav"))
    finally:
        h.close()

if __name__ == "__main__":
    print("=== Measuring Patched PM + KO2 (1MB 8MHz STE) ===", flush=True)
    res = measure_ko2_patched()
    print(res, flush=True)
    print("=== Booting Unpatched PM (1MB 8MHz STE) ===", flush=True)
    measure_unpatched_pm()
    print("Done!", flush=True)
