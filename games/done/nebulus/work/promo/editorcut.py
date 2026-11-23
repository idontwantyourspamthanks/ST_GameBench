#!/usr/bin/env python3
"""Cut the editorcap.py recordings into highlight clips (map sweep, live colour preview, playtest) using the logged times (seconds x 50 = AVI frame)."""
import json, subprocess, sys
from pathlib import Path
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/home/ryan/Videos/AtariST/Nebulus-promos/release')
ED = OUT / 'editor'; CL = ED / 'clips'; CL.mkdir(exist_ok=True)
CUTS = (('map', 'editor_open', 'vsweep_end'), ('colours', 'colours_open', 'colours_end'), ('playtest', 'playtest_running', 'playtest_end'))
for name in ('squeeze', 'escalator', 'nomansland'):
    ev = json.load(open(ED / f'{name}.json'))
    for tag, a, b in CUTS:
        f0, f1 = int(ev[a] * 50), int(ev[b] * 50)
        vf = f"select='between(n,{f0},{f1})',setpts=N/(50*TB),scale=1280:800:flags=neighbor"
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(ED / f'{name}.avi'), '-vf', vf, '-r', '50', '-an', '-c:v', 'libx264', '-crf', '12', '-pix_fmt', 'yuv420p',
                        str(CL / f'{name}_{tag}.mp4')], check=True)
        print(name, tag, f'{(f1 - f0) / 50:.1f}s')
