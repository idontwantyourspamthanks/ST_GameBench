import os, sys, time, glob, pathlib, subprocess
from PIL import Image

sys.path.insert(0, "tools")
from stharness import Hatari

ROOT = pathlib.Path("games/in_progress/player-manager")
WORK = ROOT / "work"
TOS = pathlib.Path("tos/TOS_1_62.img")

def capture_snapshots():
    h = Hatari(game_dir=str(ROOT / "build/game"),
               snapshot=str(WORK / "t2_ko2_LAUNCHED.sav"), machine="ste", memsize_kb=1024)
    try:
        h.debug(f"loadbin {WORK}/micro_opt.bin $b3000", wait=0.2)
        h.click()
        time.sleep(10.0)
        a4 = 0x284aa
        # Enable Watch mode so both teams play actively
        h.debug(f"w ${a4-0x4ef0:x} $00 $01", wait=0.05)
        # Wait for kickoff walkout to finish and active play (dFRM > 20) to begin!
        for _ in range(25):
            if h.peekl(a4 - 0x4f4e) > 20:
                break
            time.sleep(0.8)
        time.sleep(1.5)
        # Measure active play VBL/frame!
        v0, f0 = h.peekl(0x462), h.peekl(a4 - 0x4f4e)
        time.sleep(3.0)
        v1, f1 = h.peekl(0x462), h.peekl(a4 - 0x4f4e)
        dv, df = v1 - v0, f1 - f0
        vpf = dv / max(1, df)
        fps = df / max(1, dv) * 50.0
        scale = h.peekw(a4 - 0x0e0a)
        print(f"[ACTIVE MEASURE] dVBL={dv} dFRM={df} -> {fps:.2f} FPS ({vpf:.3f} VBL/frame), radar scale={scale}", flush=True)
        h.savemem(str(WORK / "v11_live_watch.sav"))

        # Cycle X until radar scale == 8 (largest radar!)
        for _ in range(6):
            if h.peekw(a4 - 0x0e0a) == 8:
                break
            h.keypress(0x2d)  # ST scancode for 'X'
            time.sleep(0.35)
        sc8 = h.peekw(a4 - 0x0e0a)
        time.sleep(0.5)
        v2, f2 = h.peekl(0x462), h.peekl(a4 - 0x4f4e)
        time.sleep(2.5)
        v3, f3 = h.peekl(0x462), h.peekl(a4 - 0x4f4e)
        dv2, df2 = v3 - v2, f3 - f2
        print(f"[SCALE={sc8} MEASURE] dVBL={dv2} dFRM={df2} -> {df2/max(1,dv2)*50:.2f} FPS ({dv2/max(1,df2):.3f} VBL/frame)", flush=True)
        h.savemem(str(WORK / "v11_live_scale8.sav"))
    finally:
        h.close()

def record_and_audit(sav_name, tag, n_vbls=120):
    avi_path = WORK / f"v11_{tag}.avi"
    fdir = WORK / f"avi_{tag}"
    fdir.mkdir(exist_ok=True)
    for old in fdir.glob("*.png"):
        old.unlink()

    env = os.environ.copy()
    env["SDL_VIDEODRIVER"] = "dummy"
    env["SDL_AUDIODRIVER"] = "dummy"
    cmd = [
        "hatari", "--machine", "ste", "--tos", str(TOS), "--memsize", "1024",
        "--monitor", "rgb", "--harddrive", str(ROOT / "build/game"),
        "--memstate", str(WORK / sav_name),
        "--avirecord", "--avi-vcodec", "png", "--avi-fps", "50",
        "--avi-file", str(avi_path), "--run-vbls", str(n_vbls), "--fast-forward", "true"
    ]
    subprocess.run(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    subprocess.run(["ffmpeg", "-y", "-i", str(avi_path), str(fdir / "f_%03d.png")],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    frames = sorted(fdir.glob("f_*.png"))
    rad_counts = []
    plr_counts = []
    hud_counts = []

    for fp in frames:
        im = Image.open(fp).convert("RGB")
        w, h = im.size
        # Hatari RGB AVI has borders; crop to active 320x200 area (center)
        # Standard Hatari low-res border: 384x274 or 320x200
        if w == 384 and h == 274:
            im = im.crop((32, 37, 352, 237))
        elif w > 320 and h > 200:
            x0 = (w - 320) // 2
            y0 = (h - 200) // 2
            im = im.crop((x0, y0, x0 + 320, y0 + 200))
        px = im.load()

        # 1. Radar black pixels in exact radar box (top horizontal line y=4..6 + left vertical line x=4..6)
        r_blk = 0
        rx_max = 72 if tag == "watch" else 135
        ry_max = 98 if tag == "watch" else 178
        for y in range(2, ry_max):
            for x in range(2, rx_max):
                r, g, b = px[x, y]
                if r < 10 and g < 10 and b < 10:
                    r_blk += 1
        rad_counts.append(r_blk)

        # 2. Player sprite pixels across pitch (y=0..180, x=0..319):
        #    KO2 players have strong red/orange/yellow/blue/white/skin that are NOT grass green!
        #    Grass has g > r + 20 and g > b + 20. Count bright non-grass, non-black sprite pixels (orange/red/blue/white-jersey)
        p_px = 0
        for y in range(0, 180):
            for x in range(80, 320):
                r, g, b = px[x, y]
                # Exclude grass greens & white pitch lines (white pitch lines have r==g==b>=200; jersey has colours!)
                # Count distinct red/orange/blue/skin player pixels: (r > g + 35) or (b > g + 35)
                if (r > g + 35) or (b > g + 35):
                    p_px += 1
        plr_counts.append(p_px)

        # 3. Bottom HUD pixels (y=182..198, x=0..319): black or orange text
        h_px = 0
        for y in range(182, 198):
            for x in range(0, 320):
                r, g, b = px[x, y]
                if (r < 10 and g < 10 and b < 10) or (r > 180 and g < 120 and b < 40):
                    h_px += 1
        hud_counts.append(h_px)

    rad_drops = [i+1 for i in range(1, len(rad_counts)) if rad_counts[i-1] > 50 and rad_counts[i] < rad_counts[i-1] * 0.80]
    plr_drops = [i+1 for i in range(1, len(plr_counts)) if plr_counts[i-1] > 40 and plr_counts[i] < plr_counts[i-1] * 0.78]
    hud_drops = [i+1 for i in range(1, len(hud_counts)) if hud_counts[i-1] > 50 and hud_counts[i] < hud_counts[i-1] * 0.80]

    print(f"\n=== 50 Hz AVI AUDIT [{tag}] ({len(frames)} frames) ===", flush=True)
    print(f"  Radar black px : min={min(rad_counts)} max={max(rad_counts)} drops(>20%)={len(rad_drops)} {rad_drops[:15]}", flush=True)
    print(f"  Player clr px  : min={min(plr_counts)} max={max(plr_counts)} drops(>22%)={len(plr_drops)} {plr_drops[:15]}", flush=True)
    print(f"  Bottom HUD px  : min={min(hud_counts)} max={max(hud_counts)} drops(>20%)={len(hud_drops)} {hud_drops[:15]}", flush=True)
    if plr_drops:
        for d in plr_drops[:5]:
            print(f"    sample drop f_{d:03d}: prev={plr_counts[d-2]} -> cur={plr_counts[d-1]} -> next={plr_counts[min(len(plr_counts)-1, d)]}", flush=True)

if __name__ == "__main__":
    capture_snapshots()
    record_and_audit("v11_live_watch.sav", "watch", 120)
    record_and_audit("v11_live_scale8.sav", "scale8", 120)
