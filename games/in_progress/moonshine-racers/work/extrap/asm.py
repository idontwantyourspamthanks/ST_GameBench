import subprocess, re, sys
from pathlib import Path
def assemble(path='/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/patches/mx_sync.s'):
    """vasm each `org` segment as a flat binary -> {org: bytes}"""
    src = open(path).read().splitlines()
    pre = [l for l in src if re.match(r'^\s*\w+\s+equ\s+', l)]
    segs = []; cur = None
    for l in src:
        m = re.match(r'^\s*org\s+(\S+)', l)
        if m: cur = (m.group(1), []); segs.append(cur); continue
        if cur is not None: cur[1].append(l)
    out = {}
    for org, lines in segs:
        a = int(org.replace('$', '0x'), 0)
        text = "\n".join(pre) + f"\n        org ${a:x}\n" + "\n".join(lines) + "\n"
        # all segments needed together for cross-segment labels: assemble the whole file as one source with orgs, output srec
    text = open(path).read()
    open('/tmp/mx_asm.s', 'w').write(text)
    r = subprocess.run(['vasmm68k_mot', '-Fsrec', '-s28', '-m68000', '-no-opt', '-o', '/tmp/mx_asm.srec', '/tmp/mx_asm.s', '-L', '/tmp/mx_asm.lst'], capture_output=True, text=True)
    if r.returncode: print(r.stdout, r.stderr); raise SystemExit(1)
    img = {}
    for ln in open('/tmp/mx_asm.srec'):
        if ln.startswith('S2'):
            n = int(ln[2:4], 16); a = int(ln[4:10], 16); d = bytes.fromhex(ln[10:10 + (n - 4) * 2])
            for i, b in enumerate(d): img[a + i] = b
        elif ln.startswith('S1'):
            n = int(ln[2:4], 16); a = int(ln[4:8], 16); d = bytes.fromhex(ln[8:8 + (n - 3) * 2])
            for i, b in enumerate(d): img[a + i] = b
        elif ln.startswith('S3'):
            n = int(ln[2:4], 16); a = int(ln[4:12], 16); d = bytes.fromhex(ln[12:12 + (n - 5) * 2])
            for i, b in enumerate(d): img[a + i] = b
    return img
if __name__ == '__main__':
    img = assemble()
    ks = sorted(img)
    print(len(img), "bytes", hex(ks[0]), hex(ks[-1]))
