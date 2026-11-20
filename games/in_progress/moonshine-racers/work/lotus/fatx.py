#!/usr/bin/env python3
"""List/extract a plain Atari ST FAT12 .st image (single level dirs). usage: fatx.py IMG [OUTDIR]"""
import struct, sys, os
d = open(sys.argv[1], 'rb').read()
out = sys.argv[2] if len(sys.argv) > 2 else None
bps, spc, res, nf, nd, ns, spf = struct.unpack('<H', d[11:13])[0], d[13], struct.unpack('<H', d[14:16])[0], d[16], struct.unpack('<H', d[17:19])[0], struct.unpack('<H', d[19:21])[0], struct.unpack('<H', d[22:24])[0]
fat = d[res*512:(res+spf)*512]
rootsec = res + nf*spf
datasec = rootsec + (nd*32+511)//512
def nxt(n):
    i = n*3//2; v = fat[i] | fat[i+1] << 8
    return (v >> 4) & 0xfff if n & 1 else v & 0xfff
def chain(c):
    r = []
    while 2 <= c < 0xff0 and len(r) < 4000:
        r.append(c); c = nxt(c)
    return r
def readf(c, sz):
    b = b''.join(d[(datasec+(x-2)*spc)*512:(datasec+(x-1)*spc)*512] for x in chain(c))
    return b[:sz]
def walk(raw, path):
    for i in range(0, len(raw), 32):
        e = raw[i:i+32]
        if e[0] == 0: break
        if e[0] == 0xe5 or e[11] == 0x0f: continue
        name = (e[:8].decode('latin1').rstrip() + ('.' + e[8:11].decode('latin1').rstrip() if e[8:11].strip() else ''))
        cl = struct.unpack('<H', e[26:28])[0]; sz = struct.unpack('<I', e[28:32])[0]
        full = path + name
        frag = [(x-2)*spc+datasec for x in chain(cl)][:1]
        print(f'{full:28s} attr={e[11]:02x} cl={cl:4d} size={sz:7d} chain={len(chain(cl))} sec0={frag}')
        if e[11] & 0x10 and name not in ('.', '..'):
            sub = readf(cl, 512*spc*len(chain(cl)))
            if out: os.makedirs(os.path.join(out, full), exist_ok=True)
            walk(sub, full + '/')
        elif out and not e[11] & 0x10:
            os.makedirs(os.path.dirname(os.path.join(out, full)) or out, exist_ok=True)
            open(os.path.join(out, full), 'wb').write(readf(cl, sz))
walk(d[rootsec*512:(rootsec+(nd*32+511)//512)*512], '')
