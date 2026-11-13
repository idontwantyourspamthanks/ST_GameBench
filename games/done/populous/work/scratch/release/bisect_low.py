import subprocess, sys, time
from pathlib import Path
from PIL import Image
GAME = Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous")
DEF = "pop_bgcopy pop_credit pop_fal_ym pop_fal_ym_demo pop_land_mul pop_land_score pop_noprot pop_ptr pop_ptrfix pp_bigram_cache".split()
def ok(n, mem="1024", tos="2.06"):
    (GAME / "patches" / "test_dummy.s").write_text(f"; name: test_dummy\n; default: no\n; prog: populous\n; site: $0bbf8\n; orig: 4267 4eb9 0001e750\n; data: $b9800 {n}\n        org     $0bbf8\n        clr.w   -(a7)\n        jsr     $1e750.l\n")
    out = GAME / "build" / "PopRelease" / "hd_bis"
    r = subprocess.run([sys.executable, "tools/poppatch.py", "build", "--hd", "--out", str(out), "--only", *DEF, "test_dummy"], cwd=GAME, capture_output=True, text=True)
    line = [l for l in r.stdout.splitlines() if l.startswith("built")]
    if r.returncode:
        return None, r.stdout[-300:] + r.stderr[-300:]
    subprocess.run([sys.executable, "work/scratch/release/ste60_look.py", str(out)], cwd=GAME, capture_output=True, text=True)
    px = Image.open("/tmp/ste60_12.png").convert("RGB").getpixel((300, 150))
    return px == (255, 255, 255), (line[0].split("payload")[1] if line else "")
for n in map(int, sys.argv[1:]):
    print(n, ok(n), flush=True)
