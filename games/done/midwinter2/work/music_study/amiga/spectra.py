import sys; sys.path.insert(0,'.')
from render import *
import numpy as np
fs=44100
print('tune  energy share above 3129 Hz (6258 Nyquist) / 6258 Hz (12517) / 12517 Hz (25033)   [mono mix, first 1000 ticks, Amiga native at 44.1 kHz, no LED filter]')
for n in range(1,18):
    L,R,_,_=render(n,1000,fs,False)
    x=(L+R)
    X=np.abs(np.fft.rfft(x*np.hanning(len(x))))**2
    f=np.fft.rfftfreq(len(x),1/fs)
    tot=X.sum()
    print(f'{n:2d}  {100*X[f>3129].sum()/tot:5.1f}% {100*X[f>6258].sum()/tot:5.1f}% {100*X[f>12517].sum()/tot:5.1f}%')
