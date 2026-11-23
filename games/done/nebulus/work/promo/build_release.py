#!/usr/bin/env python3
"""Draft assembly of the Nebulus v1.2 release video: footage cut to the voiceover (voice/promo.wav), drums and a boom under it.

    python3 build_release.py [OUTDIR]       -> OUTDIR/draft/nebulus_release_draft.mp4 (+ the per-segment files in draft/seg/)

Timeline (seconds, voice timestamps from the author):
  0.76 In a world where frogs climb towers (lift ride)  | 3.24 Life was unfair (stock bullet: ball waiting, frog walking, slow)
  4.68 Shots would just pass through enemies (stock bullet: fire, miss, ball knocks the frog off)
  7.16 Until one day (pause 8.12) they didn't (v1.2 bullet: the shot bursts the ball) | 9.08 He could fight back (hold)
  10.48 But evil doesn't sleep (glitch into the editor) | 12.00 It kept devising new terrors, new suffering (cuts on every 2nd beat of the 177 bpm drums)
  14.72 voice ends: beat-cut montage of the three nightmare levels, glitch title card.
Every segment is cut from the aligned 1280x800 clips in clips/ and editor/clips/ with a keyframed zoom (nearest neighbour) and written as exact frames at 50 fps.
"""
import subprocess, sys
from pathlib import Path

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/home/ryan/Videos/AtariST/Nebulus-promos/release')
CL, EC = OUT / 'clips', OUT / 'editor/clips'
DR = OUT / 'draft'; SEG = DR / 'seg'; SEG.mkdir(parents=True, exist_ok=True)
FPS = 50
BEAT = 60 / 177                      # the war-drum loop
P = 0.5                              # the dramatic pause inserted between "Until one day" and "they didn't" (the voice gets P seconds of silence at 8.12, everything after shifts)
# (name, source, src_start_frame, out_start_s, out_end_s, src frames per out frame (0 = freeze the start frame), zoom keyframes [(t_in_segment, zoom)], centre (x, y) in the 1280x800 source)
# The bullet camera: one slow push-in on the ball/frog pair (fixed centre, no pan), a pull-back as the frog falls, a creep during the freeze, then it holds.
C = (520, 440)
SEGS = [
    ('lift',      CL / 'liftbare_v12.mp4',   0, 0.00, 3.24, 1.0,  [(0, 1.0), (3.24, 1.6)], (620, 400)),
    ('unfair',    CL / 'bullet_stock.mp4',   0, 3.24, 4.64, 0.57, [(0, 1.4), (1.4, 1.7)], C),
    ('pass',      CL / 'bullet_stock.mp4',  40, 4.64, 7.16, 1.0,  [(0, 1.7), (1.3, 2.0), (2.52, 1.6)], C),
    ('poised',    CL / 'bullet_v12.mp4',     0, 7.16, 8.12, 1.0,  [(0, 1.9), (0.96, 2.05)], C),
    ('pause',     CL / 'bullet_v12.mp4',    47, 8.12, 8.12 + P, 0, [(0, 2.05), (P, 2.25)], C),
    ('burst',     CL / 'bullet_v12.mp4',    48, 8.12 + P, 9.08 + P, 1.0, [(0, 2.25), (0.96, 2.25)], C),
    ('fight',     CL / 'bullet_v12.mp4',    96, 9.08 + P, 10.48 + P, 1.0, [(0, 2.25), (1.4, 1.6)], C),
    ('editor',    EC / 'squeeze_map.mp4',   100, 10.48 + P, 11.28 + P, 1.0, [(0, 1.0), (0.8, 1.0)], (640, 400)),
    ('colours',   EC / 'squeeze_colours.mp4', 40, 11.28 + P, 12.00 + P, 1.0, [(0, 1.0), (0.72, 1.0)], (640, 400)),
]
CUTS = [   # the nightmare, cut on every 2nd beat of the 177 bpm loop starting at 12.00 + P
    ('n1', EC / 'squeeze_playtest.mp4',     40, None, None, 1.0, [(0, 1.8), (0.68, 1.4)], (540, 370)),
    ('n2', EC / 'escalator_playtest.mp4',   60, None, None, 1.0, [(0, 1.5), (0.68, 1.3)], (560, 370)),
    ('n3', EC / 'nomansland_playtest.mp4',  70, None, None, 1.0, [(0, 1.8), (0.68, 1.4)], (540, 370)),
    ('n4', EC / 'squeeze_playtest.mp4',     80, None, None, 1.0, [(0, 1.4), (0.68, 2.0)], (540, 370)),
]
OUTRO = [  # beat cuts after the voice
    ('o1', EC / 'escalator_playtest.mp4', 100, 1), ('o2', EC / 'nomansland_playtest.mp4', 84, 1), ('o3', EC / 'squeeze_playtest.mp4', 72, 1),
    ('o4', EC / 'escalator_playtest.mp4', 70, 1), ('o5', EC / 'nomansland_playtest.mp4', 100, 1), ('o6', EC / 'squeeze_playtest.mp4', 96, 1),
]
GLITCH = [(10.38 + P, 10.70 + P), (11.90 + P, 12.06 + P), (14.60 + P, 14.80 + P), (18.0 + P, 18.3 + P)]
END = 21.0 + P


def kf_expr(kf):
    """piecewise-linear expression of t from [(t, value)]"""
    e = f'{kf[-1][1]}'
    for (t0, v0), (t1, v1) in reversed(list(zip(kf, kf[1:]))):
        e = f'if(lt(t,{t1}),{v0}+({v1}-{v0})*(t-{t0})/{t1 - t0},{e})'
    return f'if(lt(t,{kf[0][0]}),{kf[0][1]},{e})'


def make_seg(name, src, s0, t0, t1, speed, kf, cen):
    n_out = round((t1 - t0) * FPS)
    n_src = int(n_out * speed) + 1
    freeze = speed == 0
    z = kf_expr(kf)
    cx, cy = cen
    pre = (f"select='eq(n,{s0})',setpts=N/({FPS}*TB),loop=loop={n_out}:size=1:start=0,fps={FPS}," if freeze else
           f"select='between(n,{s0},{s0 + n_src - 1})',setpts=(N/({FPS}*TB))/{speed},fps={FPS},")
    vf = (pre + f"scale=w='trunc(1280*({z})/2)*2':h='trunc(800*({z})/2)*2':eval=frame:flags=neighbor,"
          f"crop=1280:800:x='clip({cx}*({z})-640,0,iw-1280)':y='clip({cy}*({z})-400,0,ih-800)',format=yuv420p")
    f = SEG / f'{name}.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-vf', vf, '-frames:v', str(n_out), '-r', str(FPS), '-an', '-c:v', 'libx264', '-crf', '10', '-pix_fmt', 'yuv420p', str(f)], check=True)
    return f


def title_card(t):
    """glitchy title card as frames: black, 'NEBULUS' and 'v1.2 OUT NOW' in Press Start 2P with a jittering chromatic copy"""
    font = '/usr/local/share/fonts/p/PressStart2P_Regular.ttf'
    n = round(t * FPS)
    dt = lambda txt, size, y, col, dx: (f"drawtext=fontfile={font}:text='{txt}':fontsize={size}:fontcolor={col}:x='(w-text_w)/2+({dx})':y={y}")
    jit = "if(lt(mod(n,17),2),(random(1)-0.5)*40,0)"
    vf = ','.join([
        dt('NEBULUS', 96, 270, 'red@0.8', f'6+{jit}'), dt('NEBULUS', 96, 270, 'cyan@0.8', f'-6+{jit}'), dt('NEBULUS', 96, 270, 'white', jit),
        dt('V1.2  OUT NOW', 36, 440, 'white', jit), "noise=alls=18:allf=t", 'format=yuv420p'])
    f = SEG / 'card.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'color=c=black:s=1280x800:r={FPS}', '-vf', vf, '-frames:v', str(n), '-an', '-c:v', 'libx264', '-crf', '10', str(f)], check=True)
    return f


def main():
    files = []
    for s in SEGS:
        files.append(make_seg(*s)); print('seg', s[0], flush=True)
    t = 12.0 + P
    spans = [(t, t + 2 * BEAT), (t + 2 * BEAT, t + 4 * BEAT), (t + 4 * BEAT, t + 6 * BEAT), (t + 6 * BEAT, 14.72 + P)]
    for c, (a, b) in zip(CUTS, spans):
        name, src, s0, _, _, sp, kf, cen = c
        files.append(make_seg(name, src, s0, a, b, sp, kf, cen)); print('seg', name, flush=True)
        t = b
    for name, src, s0, nb in OUTRO:                       # one beat each
        files.append(make_seg(name, src, s0, t, t + BEAT * nb, 1.0, [(0, 1.5), (BEAT, 1.8)], (550, 370)))
        t += BEAT * nb; print('seg', name, flush=True)
    card_start = t
    files.append(title_card(END - card_start)); print('card from', round(card_start, 2), flush=True)
    lst = SEG / 'list.txt'
    lst.write_text(''.join(f"file '{f}'\n" for f in files))
    silent = DR / 'silent.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy', str(silent)], check=True)
    # glitch windows + fades
    g = ','.join(f"rgbashift=rh=-14:bh=14:enable='between(t,{a},{b})'" for a, b in GLITCH)
    n = ','.join(f"noise=alls=45:allf=t:enable='between(t,{a},{b})'" for a, b in GLITCH)
    vfx = f"{g},{n},fade=t=in:st=0:d=0.4,fade=t=out:st={END - 0.5}:d=0.5"
    # audio: voice, ticking bed (ducked at the pause), boom whose peak (2.40 s into the sample) lands on the burst, drums from 10.305 (beat on 12.00)
    A = OUT / 'audio'
    aud = (f"[1:a]atrim=0:8.12,asetpts=PTS-STARTPTS[va];[1:a]atrim=8.12,asetpts=PTS-STARTPTS[vb];"
           f"anullsrc=r=24000:cl=mono,atrim=0:{P}[vs];[va][vs][vb]concat=n=3:v=0:a=1[v];"
           f"[2:a]atrim=0:9,volume='if(between(t,7.95,{8.35 + P}),0,0.22)':eval=frame,afade=t=out:st=7.5:d=0.4[tick];"
           f"[3:a]adelay={int((6.0 + P) * 1000)}|{int((6.0 + P) * 1000)},volume=0.9[boom];"
           f"[4:a]aloop=loop=-1:size=2e9,atrim=0:{END - 10.305 - P},afade=t=in:st=0:d=0.5,volume=0.8,adelay={int((10.305 + P) * 1000)}|{int((10.305 + P) * 1000)}[dr];"
           f"[v][tick][boom][dr]amix=inputs=4:normalize=0:duration=longest,atrim=0:{END},afade=t=out:st={END - 0.7}:d=0.7[a]")
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(silent), '-i', str(OUT / 'voice/promo.wav'),
                    '-i', str(A / 'tense-clock-ticking-jam-fx-1-00-27.mp3'), '-i', str(A / 'cinematic-transition-boom-piano-hit-tomas-herudek-4-4-00-08.mp3'),
                    '-i', str(A / 'cinematic-war-drums_177bpm.wav'), '-filter_complex', f"[0:v]{vfx}[vv];{aud}", '-map', '[vv]', '-map', '[a]',
                    '-c:v', 'libx264', '-crf', '14', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-t', str(END), str(DR / 'nebulus_release_draft.mp4')], check=True)
    print('done', DR / 'nebulus_release_draft.mp4')


if __name__ == '__main__':
    main()
