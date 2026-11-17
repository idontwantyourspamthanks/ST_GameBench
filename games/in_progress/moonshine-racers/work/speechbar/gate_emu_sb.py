"""Exact 68000 model gate of the speech bar (work/tightA/gate_emu.py recipe): F = the default set (speech drawn into the sky), S = the same with sb_*.
python3 gate_emu_sb.py LIVE_F LIVE_S LEVELS KINDS NPASS [xtest=N] [poke=ADDR=HEX] [res=file.json]
Every flip (main and extra frames) of both runs, matched by order:
  A  rows 65-199: S == F                                   B0 rows 0-15: S == F
  B  rows 42-64: S is sky (15) everywhere
  C  rows 42-64: S == F outside the stock message box (112,42)-(303,64), which is excluded in frames where F has non-sky pixels there
  D  rows 16-41 of BOTH buffers == the strip rendered by the model (message text read from RAM at BM+4, BN characters, face FI) from that buffer's own shadow ($BA900 / $B2A10)
  T  the drawn buffer's shadow == the ticker state at the flip: message $11a8 / characters $11a4-$11a8-4 when $11ab != 0, else empty
  R  RAM $0-$6ffff after every pass: S == F except the kernel scratch $100c-$100d, buffer parity (extra frames flip) and the cloud-free scratch listed in MASK
  M  monotone display: within one message the character count of the DISPLAYED frames never decreases (flicker check over the flip sequence)"""
import sys, collections, json, struct
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/hud/build')
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/speechbar')
from emuhud import *
from sbart import draw_strip
A, B = sys.argv[1], sys.argv[2]; levels = [int(x) for x in sys.argv[3].split(',')]; kinds = sys.argv[4].split(','); npass = int(sys.argv[5])
opts = sys.argv[6:]
xtest = 0; pokes = []; resf = None
for o in opts:
    if o.startswith('xtest='): xtest = int(o[6:])
    if o.startswith('poke='): pokes.append((int(o[5:].split('=')[0], 16), bytes.fromhex(o.split('=')[2])))
    if o.startswith('res='): resf = o[4:]
    if o.startswith('dumps='): DUMPS = o[6:]
TICK = 30
MASK = [(0x100c, 0x100d), (0x1004, 0x100d)]                                   # kernel scratch / buffer parity
SITES = [(0xedea, 0xedef), (0xf90c, 0xf911), (0xf994, 0xf999), (0x1209c, 0x120a1), (0x120a4, 0x120a7), (0x12086, 0x12087), (0x14fd4, 0x14fd9)]   # the patch sites that differ between F and S (ta_init/hd_init, sb hooks, ta_face, ta_erase, ta_glyph, sb_*)
MASK += SITES
def run(dump, kind, live, isS):
    e = Emu(dump); apply_live_p(e, live)
    if xtest: e.setb(0xB8F21, xtest)
    if isS:
        for a, v in pokes: e.write(a, v)
    fl = []
    def at_flip(uc, a, s, u):
        b = e.l(0x1008)
        st = bytes(uc.mem_read(0x1190, 0x30))
        M = e.w(0x11a8)
        fl.append(dict(buf=bytes(uc.mem_read(b, 0x7d00)), other=bytes(uc.mem_read(0x78000 if b == 0x70000 else 0x70000, 0x7d00)), pass_=e.w(0x100e), back=b,
                       st=st, sb=bytes(uc.mem_read(0xBA900, 32)), t11ab=e.b(0x11ab), M=M, tp=e.w(0x11a4), text=bytes(uc.mem_read(0x6000, 0x1000))))
    e.uc.hook_add(UC_HOOK_CODE, at_flip, begin=0xd1ca, end=0xd1ca)
    rams = []
    for p in range(npass):
        v = schedule(p, kind)
        if v is not None: e.setb(0x6105, v)
        if xtest:
            e.setb(0xB8F08, 0); e.setl(0xB8F00, TICK * (p + 1)); e.run(0x7a88, 0xb8100); e.run(0xb8100, 0x7b7a)
        else:
            e.run(0x7a88, 0x7b74); flip(e)
        rams.append(bytes(e.uc.mem_read(0, 0x70000)))
        e.run(0x7b7a, 0x7a88)
    return fl, rams
def text_of(fr, M):
    o = M + 4 - 0x6000
    t = fr['text'][o:o + 128]
    return t.split(b'\0')[0].decode('latin1')
tot = collections.Counter(); badram = collections.Counter(); vis = []
chk = {k: [0, 0, 0] for k in ('A rows65-199 S==F', 'B0 bar rows0-15 S==F', 'B sky rows42-64 == sky', 'C rows42-64 S==F outside msgbox', 'D strip rows16-41 == model (2 buffers)')}
for L in levels:
    for kind in kinds:
        d = DUMPS % L
        fa, ra = run(d, kind, A, False); fb, rb = run(d, kind, B, True)
        n = min(len(fa), len(fb)); tot['frames'] += n; tot['frames_F'] += len(fa); tot['frames_S'] += len(fb)
        lastM = None; lastn = -1
        first = True
        for x, y in zip(fa, fb):
            fF = idx_img(x['buf']); fS = idx_img(y['buf'])
            def acc(k, comp, ex, bad):
                chk[k][0] += comp; chk[k][1] += ex; chk[k][2] += bad
            acc('A rows65-199 S==F', fS[65:].size, 0, int((fF[65:] != fS[65:]).sum()))
            acc('B0 bar rows0-15 S==F', fS[:16].size, 0, int((fF[:16] != fS[:16]).sum()))
            sky = fS[42:65]; acc('B sky rows42-64 == sky', sky.size, 0, int((sky != 15).sum()))
            dd = fF[42:65] != fS[42:65]
            active = bool((fF[42:65, 112:304] != 15).any())
            m = np.zeros((23, 320), bool)
            if active: m[:, 112:304] = True
            acc('C rows42-64 S==F outside msgbox', int((~m).sum()), int(m.sum()), int((dd & ~m).sum()))
            if active:
                ys, xs = np.nonzero(dd); vis.append((int(dd.sum()), int(ys.min()) + 42, int(ys.max()) + 42, int(xs.min()), int(xs.max())))
            # D: model of both buffers of S
            comp = bad = 0
            for k, which in enumerate((0x70000, 0x78000)):
                if first and y['back'] != which: continue          # the first flip of a run: the other buffer has not been drawn yet
                BM, BN, FI = struct.unpack('>HHH', y['sb'][16 * k:16 * k + 6])
                img = idx_img(y['buf'] if y['back'] == which else y['other'])
                ex = np.zeros((200, 320), np.uint8)
                draw_strip(ex, text_of(y, BM) if BM else None, BN, FI if FI else None)
                comp += 26 * 320; bad += int((ex[16:42] != img[16:42]).sum())
            first = False
            acc('D strip rows16-41 == model (2 buffers)', comp, 0, bad)
            kd = 0 if y['back'] == 0x70000 else 1
            BM, BN, FI = struct.unpack('>HHH', y['sb'][16 * kd:16 * kd + 6])
            nn = (y['tp'] - y['M'] - 4) & 0xffff
            tick = (BM, BN) == ((y['M'], nn) if y['t11ab'] else (0, 0)) and ((FI != 0) == bool(y['t11ab']))
            tot['ticker_ok'] += tick; tot['ticker_n'] += 1
            # M: displayed frame = the drawn buffer after the flip
            if BM:
                if BM == lastM and BN < lastn: tot['nonmonotone'] += 1
                lastM, lastn = BM, BN
            else:
                lastM, lastn = None, -1
        for pa, pb in zip(ra, rb):
            if pa != pb:
                a = np.frombuffer(pa, np.uint8); b = np.frombuffer(pb, np.uint8)
                for i in np.nonzero(a != b)[0]:
                    if any(lo <= i <= hi for lo, hi in MASK): tot['masked_bytes'] += 1; continue
                    badram[int(i)] += 1
        print('level', L, kind, 'flips', n, '(F %d S %d)' % (len(fa), len(fb)), dict(tot), 'bad RAM addrs', len(badram), flush=True)
ok = all(v[2] == 0 for v in chk.values()) and tot['ticker_ok'] == tot['ticker_n'] and not badram and tot['nonmonotone'] == 0
print('RESULT', 'IDENTICAL' if ok else 'DIFFER')
for k, (c, ex, bad) in chk.items(): print(f'  {k:40s} compared {c:11d} excluded {ex:9d} differing {bad:7d} -> {"IDENTICAL" if bad == 0 else "DIFFER"}')
print(f"  T drawn-buffer shadow == ticker state: {tot['ticker_ok']}/{tot['ticker_n']} flips;  M non-monotone displayed sequences: {tot['nonmonotone']};  frames F/S {tot['frames_F']}/{tot['frames_S']}")
print(f"  R RAM $0-$6ffff per pass: differing addresses {len(badram)} (masked bytes {tot['masked_bytes']})")
for a, nn in sorted(badram.items())[:30]: print('    RAM $%05x differs in %d passes' % (a, nn))
if vis: print(f"  E visible differences below the strip: {len(vis)} frames with a stock message box; rows {min(v[1] for v in vis)}-{max(v[2] for v in vis)}, columns {min(v[3] for v in vis)}-{max(v[4] for v in vis)}, mean differing pixels {sum(v[0] for v in vis)/len(vis):.0f}")
if resf: json.dump(dict(chk=chk, tot=dict(tot), badram={hex(k): v for k, v in badram.items()}), open(resf, 'w'))
