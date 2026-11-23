#!/usr/bin/env python3
"""Cut the capture.py AVIs into aligned clips.

    python3 post.py [OUTDIR]      (default /home/ryan/Videos/AtariST/Nebulus-promos/release)

For every scenario the stock and v12 clips start on the SAME game frame: the first flip after the scene was poked (loop index 0), and
every later flip sits at  frame = A + (flip VBL - first flip VBL)  (Hatari records one AVI frame per emulated VBL).
  bullet: A = the frame of the big scene change (the stack vanishes and the ball appears at the event).
  lift:   A is found by matching the logged flip VBLs (stock has 3-VBL loops, so the pattern is not periodic) against the frames that
          changed in the video; the v12 clip is anchored by the frame where the ride starts to scroll (the same loop in both runs).
Output (OUTDIR/clips): <scenario>_<variant>.mp4 (H.264 crf 10, yuv420p, 1280x800 = 4x the ST screen, nearest neighbour, 50 fps),
<scenario>_<variant>_flips.json (per game loop: clip frame, VBL spent in the loop) and a fps summary in clips/summary.txt.
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/home/ryan/Videos/AtariST/Nebulus-promos/release')
RAW, CLIPS = OUT / 'raw', OUT / 'clips'
CLIPS.mkdir(exist_ok=True)


def diffs(tag):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(RAW / f'{tag}.avi'), '-vf', 'scale=160:100:flags=area', '-pix_fmt', 'gray', '-f', 'rawvideo', '-'],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(-1, 100, 160).astype(int)
    return np.abs(np.diff(a, axis=0)).mean(axis=(1, 2))          # d[i] = frame i+1 vs frame i


def spike_start(d, thr=5.0):
    return int(np.argmax(d > thr)) + 1


def scroll_start(d):          # first frame of the ride's whole-screen scroll
    return int(np.argmax(d > 10.0)) + 1


def match_start(d, flips):
    changed = np.r_[False, d > 0]
    rel = np.array(flips) - flips[0]
    best = None
    for A in range(0, len(changed) - int(rel[-1]) - 1):
        p = A + rel
        s = int(changed[p].sum()) - int((~changed[p]).sum())
        if best is None or s > best[0]:
            best = (s, A)
    return best[1], best[0], len(rel)


def main():
    lines = []
    anchors = {}
    for sc in ('bullet', 'lift', 'liftbare'):
        for var in ('stock', 'v12'):
            tag = f'{sc}_{var}'
            d = diffs(tag)
            m = json.load(open(RAW / f'{tag}.json'))
            fl = m['flips']
            if sc == 'bullet':
                A = spike_start(d)
                changed = np.r_[False, d > 0]
                p = A + np.array(fl) - fl[0]
                chk = f'{int(changed[p].sum())}/{len(p)} logged flips land on a changed frame'
            elif var == 'stock':
                A, score, n = match_start(d, fl)
                chk = f'flip-pattern match score {score}/{n}'
                anchors['lift_scroll_off'] = scroll_start(d) - A
            else:
                A = scroll_start(d) - anchors['lift_scroll_off']
                changed = np.r_[False, d > 0]
                p = A + np.array(fl) - fl[0]
                chk = f'{int(changed[p].sum())}/{len(p)} logged flips land on a changed frame'
            last = A + fl[-1] - fl[0] + 2
            nfr = last - A
            rel = [int(v - fl[0]) for v in fl]
            gaps = [b - a for a, b in zip(fl, fl[1:])]
            (CLIPS / f'{tag}_flips.json').write_text(json.dumps(dict(start_frame=A, frames=nfr, loop_vbl=gaps, loop_frame=[A + r for r in rel])))
            vf = f"select='between(n,{A},{last-1})',setpts=N/(50*TB),scale=1280:800:flags=neighbor"
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(RAW / f'{tag}.avi'), '-vf', vf, '-r', '50', '-an', '-c:v', 'libx264', '-crf', '10',
                            '-preset', 'slow', '-pix_fmt', 'yuv420p', str(CLIPS / f'{tag}.mp4')], check=True)
            fps = 50.0 * len(gaps) / sum(gaps)
            lines.append(f'{tag}: start frame {A}, {nfr} frames ({nfr/50:.2f} s), {len(gaps)+1} loops, mean {sum(gaps)/len(gaps):.3f} VBL/loop = {fps:.2f} fps, loops over 2 VBL: {sum(1 for g in gaps if g > 2)}; {chk}')
            print(lines[-1], flush=True)
    (CLIPS / 'summary.txt').write_text('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
