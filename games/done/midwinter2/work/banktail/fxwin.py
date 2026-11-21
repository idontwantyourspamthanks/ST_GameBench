#!/usr/bin/env python3
"""Per-effect window statistics of walk.py --fx captures: the window of effect k = [request k, request k+1) (the last one 10 s), the capture runs in emulated time
(Hatari drops no samples between requests: the debugger pauses are short) so the window starts are the logged request times (wall seconds since the capture start).
Prints rms, peak, spectral flatness (1 = white noise), spectral centroid and the share of the energy above 1.5 kHz.  Compare a good machine with the damaged one:
the damaged engine loops are mostly zeros with isolated pointer/vector bytes.
   usage: fxwin.py A.wav id:t,id:t,... [B.wav id:t,...]   (times from the 'requested:' line of work/banktail/out/<cell>.txt)"""
import sys, wave
import numpy as np
def load(p):
    with wave.open(str(p), "rb") as w:
        n, ch, sw, r = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate(); raw = w.readframes(n)
    x = np.frombuffer(raw, dtype="<i2").astype(float)
    if ch == 2: x = x.reshape(-1, 2).mean(axis=1)
    return x - x.mean(), r
def stats(x, r):
    sp = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2 + 1e-9
    f = np.fft.rfftfreq(len(x), 1 / r)
    return dict(rms=float(np.sqrt((x ** 2).mean())), peak=float(np.abs(x).max()), flat=float(np.exp(np.log(sp).mean()) / sp.mean()),
                cen=float((f * sp).sum() / sp.sum()), hi=float(sp[f > 1500].sum() / sp.sum()))
def run(p, spec):
    x, r = load(p)
    ts = [(int(a.split(":")[0]), float(a.split(":")[1])) for a in spec.split(",")]
    out = []
    for k, (sid, t) in enumerate(ts):
        t1 = ts[k + 1][1] if k + 1 < len(ts) else t + 10
        s = x[int(t * r):int(min(t1, t + 10) * r)]
        out.append((sid, stats(s, r)))
    return out
if __name__ == "__main__":
    res = []
    for i in range(1, len(sys.argv), 2):
        res.append((sys.argv[i], run(sys.argv[i], sys.argv[i + 1])))
    for name, rows in res:
        print(name)
        for sid, s in rows:
            print(f"  id {sid:2d}: rms {s['rms']:7.0f} peak {s['peak']:7.0f} flatness {s['flat']:.4f} centroid {s['cen']:6.0f} Hz  energy>1.5kHz {100*s['hi']:5.1f} %")
