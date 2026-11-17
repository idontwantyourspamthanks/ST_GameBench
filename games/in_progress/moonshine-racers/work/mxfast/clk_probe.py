import sys, re
from hlib import *
h = open_snap('ste1m_race_start.sav', 8)
try:
    f = h.R / 'probe.txt'
    f.write_text("e VBL\ne FrameCycles\nm $4ba 4\nm $ff8205 1\nm $ff8207 1\nm $ff8209 1\nm $ff8201 1\nm $ff8203 1\nm $611b 1\n")
    n0 = len(h._logtext())
    # sample at several breakpoints inside the pass loop top
    for i in range(8):
        h.cmd(f"hatari-debug b pc = $796a :trace :once :file {f}"); time.sleep(0.5)
    o = h._logtext()[n0:]
    for seg in o.split('> e VBL')[1:]:
        g = mem_parse(seg); v = re.findall(r"#(\d+) \(dec\)", seg)
        hz = int.from_bytes(bytes(g[0x4ba + k] for k in range(4)), 'big') if 0x4ba in g else None
        print(v, 'hz200', hz, {hex(a): g.get(a) for a in (0xff8205, 0xff8207, 0xff8209, 0xff8201, 0xff8203)})
finally:
    h.close()
