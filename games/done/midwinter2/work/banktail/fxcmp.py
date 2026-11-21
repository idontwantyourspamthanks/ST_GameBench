#!/usr/bin/env python3
"""Compare the effect captures of two walk.py --fx runs (same id list): per effect segment duration / rms / peak / spectral flatness, and the
normalised cross-correlation of segment k of A against segment k of B (lag search +-100 ms).  Control: an effect outside the damaged tail must correlate ~1.
   usage: fxcmp.py A.wav B.wav ID,ID,... [thr]"""
import sys
import numpy as np
sys.path.insert(0, "/home/ryan/Code/AtariST/gamebench/games/done/midwinter2/tools")
import wave

def load(p):
    with wave.open(str(p), "rb") as w:
        n, ch, sw, rate = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(n)
    x = np.frombuffer(raw, dtype="<i2" if sw == 2 else "u1").astype(float)
    if ch == 2: x = x.reshape(-1, 2).mean(axis=1)
    return x - x.mean(), rate

def segments(x, rate, thr, gap=0.8, win=0.02):
    k = int(win * rate); n = len(x) // k
    e = np.sqrt((x[:n * k].reshape(n, k) ** 2).mean(axis=1))
    on = e > thr
    segs = []; i = 0
    while i < n:
        if on[i]:
            j = i; last = i
            while j < n and j - last < gap / win:
                if on[j]: last = j
                j += 1
            segs.append((i * k, (last + 1) * k)); i = last + 1
        else: i += 1
    return segs

def flat(s):
    sp = np.abs(np.fft.rfft(s * np.hanning(len(s)))) ** 2 + 1e-9
    return float(np.exp(np.log(sp).mean()) / sp.mean())

def xcorr(a, b, rate, maxlag=0.1):
    n = min(len(a), len(b), int(2.0 * rate))
    a, b = a[:n], b[:n]
    F = np.fft.rfft(a, 2 * n) * np.conj(np.fft.rfft(b, 2 * n))
    c = np.fft.irfft(F)
    L = int(maxlag * rate)
    c = np.concatenate([c[-L:], c[:L + 1]])
    return float(c.max() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-9))

A, ra = load(sys.argv[1]); B, rb = load(sys.argv[2])
ids = [int(v) for v in sys.argv[3].split(",")]
thr = float(sys.argv[4]) if len(sys.argv) > 4 else 60
sa, sb = segments(A, ra, thr), segments(B, rb, thr)
print(f"A {sys.argv[1]}: {len(A)/ra:.1f} s, {len(sa)} segments; B {sys.argv[2]}: {len(B)/rb:.1f} s, {len(sb)} segments (expected {len(ids)})")
for k in range(max(len(sa), len(sb))):
    row = []
    for S, X, r in ((sa, A, ra), (sb, B, rb)):
        if k < len(S):
            s = X[S[k][0]:S[k][1]]
            row.append(f"{(S[k][1]-S[k][0])/r:5.2f}s rms {np.sqrt((s**2).mean()):7.0f} peak {np.abs(s).max():7.0f} flat {flat(s[:int(r*1.0)]):.3f}")
        else: row.append("-")
    c = xcorr(A[sa[k][0]:sa[k][1]], B[sb[k][0]:sb[k][1]], ra) if k < len(sa) and k < len(sb) and ra == rb else float("nan")
    print(f"seg {k} (id {ids[k] if k < len(ids) else '?'}): A [{row[0]}] | B [{row[1]}] | xcorr {c:.3f}")
