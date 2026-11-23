#!/usr/bin/env python3
"""Release video v2: the author's own voice (voice/my-voice-001..011.wav, one wav per phrase) with a voice-over treatment, and a title card first (so the Twitter
thumbnail is the title).  Picture segments and helpers come from build_release.py; this file re-times them to the new phrase lengths.

    python3 build_release_v2.py [OUTDIR]  ->  OUTDIR/draft/nebulus_release_v2_myvoice.mp4  (+ draft/voice_v2_fx.wav, the treated voice alone)

Timeline (seconds, before the title card; the card adds CARD seconds in front of everything):
  phrase starts (speech, not file, start):  01 .80  02 1.60  03 2.55 | 04 3.95 | 05 5.65 | 06 8.75 .. pause .. 07 10.62 | 08 11.35 | 09 12.95 | 10 14.75 | 11 17.80
  picture: lift ride | stock bullet slowed (waiting ball) | fire at 5.75, shot passes through, frog knocked off | v1.2 bullet slowed to the poised frog (freeze 10.22-10.62)
           shot flies on "they", burst on "didn't" | hold | editor + colours | beat cuts (every 2nd beat of 177 bpm from 14.75) | end card.
Voice treatment: per-phrase level match, high-pass, low-shelf and presence EQ, compression, a -3 semitone double (-9 dB), a synthetic hall reverb (convolved noise
tail, wet -14 dB) and a limiter; the music bed is ducked under the voice with a sidechain compressor.
"""
import subprocess, sys, wave
from pathlib import Path
import numpy as np
sys.argv = sys.argv[:1] + sys.argv[1:2]
import build_release as B

OUT = B.OUT
DR, SEG, A, V = B.DR, B.SEG, OUT / 'audio', OUT / 'voice'
CL, EC = B.CL, B.EC
CARD = 2.0
BEAT = B.BEAT
C = (520, 440)
END = 23.0                                    # end of the picture before the card is added in front
PAUSE = (10.22, 10.62)
PHRASE_START = {1: 0.80, 2: 1.60, 3: 2.55, 4: 3.95, 5: 5.65, 6: 8.75, 7: 10.62, 8: 11.35, 9: 12.95, 10: 14.75, 11: 17.80}
BURST = 10.62 + 0.28                          # the burst frame of the v1.2 clip (src 62) lands on "didn't"
SEGS = [
    ('v2_lift',     CL / 'liftbare_v12.mp4',    0, 0.00, 3.95, 1.0,  [(0, 1.0), (3.95, 1.6)], (620, 400)),
    ('v2_unfair',   CL / 'bullet_stock.mp4',    0, 3.95, 5.75, 48 / 90, [(0, 1.4), (1.8, 1.8)], C),
    ('v2_pass',     CL / 'bullet_stock.mp4',   48, 5.75, 8.75, 1.0,  [(0, 1.8), (1.3, 2.0), (3.0, 1.6)], C),
    ('v2_poised',   CL / 'bullet_v12.mp4',      0, 8.75, PAUSE[0], 47 / 73.5, [(0, 1.9), (PAUSE[0] - 8.75, 2.05)], C),
    ('v2_pause',    CL / 'bullet_v12.mp4',     47, PAUSE[0], PAUSE[1], 0, [(0, 2.05), (PAUSE[1] - PAUSE[0], 2.2)], C),
    ('v2_burst',    CL / 'bullet_v12.mp4',     48, PAUSE[1], PAUSE[1] + 0.96, 1.0, [(0, 2.2), (0.96, 2.2)], C),
    ('v2_fight',    CL / 'bullet_v12.mp4',     96, PAUSE[1] + 0.96, 12.70, 1.0, [(0, 2.2), (12.70 - PAUSE[1] - 0.96, 1.7)], C),
    ('v2_editor',   EC / 'squeeze_map.mp4',   100, 12.70, 13.50, 1.0, [(0, 1.0), (0.8, 1.0)], (640, 400)),
    ('v2_colours',  EC / 'squeeze_colours.mp4', 40, 13.50, 14.75, 1.0, [(0, 1.0), (1.25, 1.0)], (640, 400)),
]
CUTS = [('v2_n1', 'squeeze_playtest', 40, (1.8, 1.4), (540, 370)), ('v2_n2', 'escalator_playtest', 60, (1.5, 1.3), (560, 370)),
        ('v2_n3', 'nomansland_playtest', 70, (1.8, 1.4), (540, 370)), ('v2_n4', 'squeeze_playtest', 80, (1.4, 2.0), (540, 370)),
        ('v2_n5', 'escalator_playtest', 100, (1.4, 1.8), (560, 370)), ('v2_n6', 'nomansland_playtest', 84, (1.6, 1.4), (540, 370)),
        ('v2_n7', 'squeeze_playtest', 96, (1.4, 1.9), (540, 370))]
OUTRO = [('v2_o1', 'escalator_playtest', 70), ('v2_o2', 'nomansland_playtest', 100), ('v2_o3', 'squeeze_playtest', 72), ('v2_o4', 'escalator_playtest', 130)]
GLITCH = [(12.55, 12.85), (14.60, 14.85), (END - 2.2, END - 1.9)]


def title_card(t, name, lines, glitch=True):
    font = '/usr/local/share/fonts/p/PressStart2P_Regular.ttf'
    jit = "if(lt(mod(n,17),2),(random(1)-0.5)*40,0)"
    dt = lambda txt, size, y, col, dx: f"drawtext=fontfile={font}:text='{txt}':fontsize={size}:fontcolor={col}:x='(w-text_w)/2+({dx})':y={y}"
    parts = [dt(lines[0], 96, 270, 'red@0.8', f'6+{jit}'), dt(lines[0], 96, 270, 'cyan@0.8', f'-6+{jit}'), dt(lines[0], 96, 270, 'white', jit)]
    parts += [dt(lines[1], 28, 440, 'white', jit), 'noise=alls=18:allf=t', 'format=yuv420p']
    f = SEG / f'{name}.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'color=c=black:s=1280x800:r={B.FPS}', '-vf', ','.join(parts), '-frames:v', str(round(t * B.FPS)),
                    '-an', '-c:v', 'libx264', '-crf', '10', str(f)], check=True)
    return f


def make_ir(path, secs=1.8, sr=44100):
    rng = np.random.default_rng(7)
    n = int(secs * sr)
    t = np.arange(n) / sr
    ir = np.zeros((n, 2))
    for ch in range(2):
        x = rng.standard_normal(n) * np.exp(-t / 0.42)
        k = 40
        x = np.convolve(x, np.ones(k) / k, 'same')                      # darker tail
        x[: int(0.025 * sr)] = 0                                       # 25 ms pre-delay
        ir[:, ch] = x
    ir /= np.abs(ir).max()
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((ir * 32000).astype('<i2').tobytes())


def phrase_info(i):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(V / f'my-voice-{i:03d}.wav'), '-ac', '1', '-ar', '16000', '-f', 's16le', '-'], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.int16).astype(float)
    w = 160
    e = np.sqrt(np.convolve(a ** 2, np.ones(w) / w, 'same'))
    idx = np.nonzero(e > max(e.max() * 0.05, 150))[0]
    s, t = idx[0] / 16000, idx[-1] / 16000
    seg = a[idx[0]:idx[-1]]
    rms_db = 20 * np.log10(np.sqrt((seg ** 2).mean()) / 32768)
    return s, t, rms_db


def build_voice():
    ir = DR / 'ir_hall.wav'; make_ir(ir)
    inputs, chains, labels = [], [], []
    for k, i in enumerate(range(1, 12)):
        s, t, db = phrase_info(i)
        gain = -20.0 - db                                               # every phrase to -20 dBFS speech RMS
        delay = int(round((PHRASE_START[i] + CARD - s) * 1000))
        inputs += ['-i', str(V / f'my-voice-{i:03d}.wav')]
        chains.append(f"[{k}:a]pan=mono|c0=0.5*c0+0.5*c1,aresample=44100,volume={gain:.1f}dB,afade=t=in:st=0:d=0.01,adelay={delay}|{delay}[p{i}]")
        labels.append(f'[p{i}]')
    inputs += ['-i', str(ir)]
    ik = 11
    fx = (''.join(c + ';' for c in chains) + ''.join(labels) + f"amix=inputs=11:normalize=0:duration=longest[dry0];"
          f"[dry0]highpass=f=75,bass=g=4:f=180,equalizer=f=3500:t=q:w=1:g=3,acompressor=threshold=0.06:ratio=3.5:attack=8:release=180:makeup=2,asplit=3[d][pd][rv];"
          f"[pd]asetrate=44100*0.8409,aresample=44100,atempo=1.1892,volume=0.35[dbl];"
          f"[rv][{ik}:a]afir=dry=0:wet=1,volume=0.20[wet];"
          f"[d][dbl][wet]amix=inputs=3:normalize=0:duration=longest,alimiter=limit=0.9,aformat=sample_fmts=fltp:channel_layouts=stereo,asplit=2[voice][vsc]")
    return inputs, fx


def main():
    files = []
    for name, src, s0, t0, t1, sp, kf, cen in SEGS:
        files.append(B.make_seg(name, src, s0, t0, t1, sp, kf, cen)); print('seg', name, flush=True)
    t = 14.75
    for name, clip, s0, kf, cen in CUTS:
        files.append(B.make_seg(name, EC / f'{clip}.mp4', s0, t, t + 2 * BEAT, 1.0, [(0, kf[0]), (2 * BEAT, kf[1])], cen)); t += 2 * BEAT; print('seg', name, flush=True)
    for name, clip, s0 in OUTRO:
        files.append(B.make_seg(name, EC / f'{clip}.mp4', s0, t, t + BEAT, 1.0, [(0, 1.5), (BEAT, 1.8)], (550, 370))); t += BEAT
    files.append(title_card(END - t, 'v2_end', ('NEBULUS', 'ENHANCED  V1.2  OUT NOW')))
    head = title_card(CARD, 'v2_head', ('NEBULUS', 'ENHANCED EDITION  V1.2'))
    (SEG / 'list_v2.txt').write_text(''.join(f"file '{f}'\n" for f in [head] + files))
    silent = DR / 'silent_v2.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(SEG / 'list_v2.txt'), '-c', 'copy', str(silent)], check=True)
    total = END + CARD
    g = ','.join(f"rgbashift=rh=-14:bh=14:enable='between(t,{a + CARD},{b + CARD})'" for a, b in GLITCH)
    n = ','.join(f"noise=alls=45:allf=t:enable='between(t,{a + CARD},{b + CARD})'" for a, b in GLITCH)
    vfx = f"{g},{n},fade=t=out:st={total - 0.5}:d=0.5"
    inputs, fx = build_voice()
    off = len(inputs) // 2                                              # index of the first extra input after the 11 phrases + IR
    bed = (f"[{off}:a]atrim=0:{PAUSE[0] + CARD},volume='0.22*clip(({PAUSE[0] + CARD}-t)/0.25,0,1)':eval=frame[tick];"
           f"[{off + 1}:a]adelay={int((BURST + CARD - 2.40) * 1000)}|{int((BURST + CARD - 2.40) * 1000)},volume=0.9[boom];"
           f"[{off + 2}:a]aloop=loop=-1:size=2e9,atrim=0:{total - (14.75 + CARD - 5 * BEAT)},afade=t=in:st=0:d=0.6,volume=0.8,"
           f"adelay={int((14.75 + CARD - 5 * BEAT) * 1000)}|{int((14.75 + CARD - 5 * BEAT) * 1000)}[dr];"
           f"[tick][dr]amix=inputs=2:normalize=0:duration=longest,aformat=sample_fmts=fltp:channel_layouts=stereo[music];"
           f"[music][vsc]sidechaincompress=threshold=0.02:ratio=6:attack=15:release=350[duck];"
           f"[voice][duck][boom]amix=inputs=3:normalize=0:duration=longest,volume=-1.5dB,alimiter=limit=0.89:level=false,atrim=0:{total},afade=t=out:st={total - 0.7}:d=0.7[a]")
    extra = ['-i', str(A / 'tense-clock-ticking-jam-fx-1-00-27.mp3'), '-i', str(A / 'cinematic-transition-boom-piano-hit-tomas-herudek-4-4-00-08.mp3'),
             '-i', str(A / 'cinematic-war-drums_177bpm.wav')]
    # the treated voice alone first (for judging the levels)
    subprocess.run(['ffmpeg', '-v', 'error', '-y'] + inputs + ['-filter_complex', fx.replace(',asplit=2[voice][vsc]', '[voice]'), '-map', '[voice]', '-t', str(total), str(DR / 'voice_v2_fx.wav')], check=True)
    # inputs are indexed after the video: shift every audio input index by one
    shifted = fx
    for k in range(11, -1, -1):
        shifted = shifted.replace(f'[{k}:a]', f'[{k + 1}:a]')
    bed2 = bed
    for k in range(off + 2, off - 1, -1):
        bed2 = bed2.replace(f'[{k}:a]', f'[{k + 1}:a]')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(silent)] + inputs + extra + ['-filter_complex', f"[0:v]{vfx}[vv];{shifted};{bed2}", '-map', '[vv]', '-map', '[a]',
                    '-c:v', 'libx264', '-crf', '14', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-t', str(total), str(DR / 'nebulus_release_v2_myvoice.mp4')], check=True)
    print('done', DR / 'nebulus_release_v2_myvoice.mp4')


if __name__ == '__main__':
    main()
