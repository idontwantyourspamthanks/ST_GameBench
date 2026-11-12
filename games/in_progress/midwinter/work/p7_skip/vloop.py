"""vloop.py: run_checks(h, live_prefix, K, ...) = the skip self-check of verify.py on an existing Hatari session (cold boot too).
For each check: arm a breakpoint at the hook's `.skip` label; at the skip decision save the 3 screen buffers (A), force the render
(r pc = .render), save them again at $14e72 (B); a skipped frame is right iff A == B."""
import json, time, struct
from pathlib import Path
import numpy as np

def locate(live):
    img = Path(live + '.img').read_bytes(); base = json.loads(Path(live + '.json').read_text())['img_base']
    p1 = img.find(bytes.fromhex('52ae00104cdf7fff588f')); assert p1 >= 0
    p2 = img.find(bytes.fromhex('4cdf7fff23df000b600c')); assert p2 >= 0
    return base + p1, base + p2

def run_checks(h, live, K, maxwait=90, V='/tmp/p7s/v', log=print, between=None):
    SKIP, RENDER = locate(live)
    V = Path(V); V.mkdir(exist_ok=True)
    for f in V.glob('*'): f.unlink()
    chk = V / 'chk.txt'
    chk.write_text("".join(f"savebin {V}/b{n}.bin ${ad:x} $7d00\n" for n, ad in (('58', 0x58000), ('68', 0x68000), ('78', 0x78000)))
                   + f"savebin {V}/done.bin $b6000 $60\nsavebin {V}/buf.bin $12d0a 4\n")
    skp = V / 'skip.txt'
    skp.write_text("".join(f"savebin {V}/a{n}.bin ${ad:x} $7d00\n" for n, ad in (('58', 0x58000), ('68', 0x68000), ('78', 0x78000)))
                   + f"b pc = $14e72 :once :trace :file {chk}\nr pc=${RENDER:x}\n")
    ok = bad = 0
    for k in range(K):
        for f in V.glob('*.bin'): f.unlink()
        h.cmd(f"hatari-debug b pc = ${SKIP:x} :once :trace :file {skp}")
        t = time.time()
        while not (V / 'done.bin').exists():
            if time.time() - t > maxwait:
                log(f'no skip decision within {maxwait} s (check {k})'); return ok, bad
            time.sleep(0.2)
        time.sleep(0.4)
        d = {n: int((np.fromfile(V / f'a{n}.bin', dtype=np.uint8) != np.fromfile(V / f'b{n}.bin', dtype=np.uint8)).sum()) for n in ('58', '68', '78')}
        same = not any(d.values()); ok += same; bad += not same
        if not same or k % 10 == 0:
            raw = (V / 'done.bin').read_bytes()
            log(f'check {k}: differing bytes {d} {"OK" if same else "MISMATCH"} GEN {struct.unpack(">H", raw[4:6])[0]} NSKIP {struct.unpack(">I", raw[16:20])[0]}')
        if between: between(k)
    return ok, bad
