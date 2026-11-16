#!/usr/bin/env python3
"""RAM survey for the music bank: cold boot of an HD build whose ASNBANK.BIN is padded with a pattern (word = address ^ $A55A) up to $E83E0,
dump $B0000-$FFFFF at every screen and report (a) pattern bytes destroyed, (b) the extent of non-zero / changing bytes above the pattern.
    python3 work/asn_mus/ramsurvey.py NAME BUILD_DIR BANK [machine tos mem]
Dumps: /tmp/asn_mus/NAME/*.bin (scratch), report: work/asn_mus/NAME.txt"""
import sys, time, shutil, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from mw2harness import Hatari

name, bdir, bankf = sys.argv[1:4]
machine = sys.argv[4] if len(sys.argv) > 4 else "ste"
tosn = sys.argv[5] if len(sys.argv) > 5 else "162"
mem = int(sys.argv[6]) if len(sys.argv) > 6 else 1024
TOSD = ROOT.parent.parent.parent / "tos"
TOS = {"162": TOSD / "TOS_1_62.img", "206": TOSD / "TOS_2_06.img", "104": TOSD / "TOS_1_04.img"}
out = Path("/tmp/asn_mus") / name
shutil.rmtree(out, ignore_errors=True)
out.mkdir(parents=True)
bank = (ROOT / bankf).read_bytes()
BANK = 0xBB000
LO, HI = 0xB0000, 0x100000
log = []


def L(*a):
    s = " ".join(str(x) for x in a)
    log.append(s)
    print(s, flush=True)


h = Hatari(snapshot=None, memsize_kb=mem, machine=machine, tos=TOS[tosn], game_dir=ROOT / bdir)
dumps = []


def dump(tag):
    p = h.R / f"d_{tag}.bin"
    h.debug(f"savebin {p} ${LO:x} ${HI - LO:x}", 3.0)
    q = out / f"{tag}.bin"
    shutil.copy(p, q)
    p.unlink()
    shutil.copy(h.shot(), out / f"{tag}.png")
    d = q.read_bytes()
    bad = [i for i in range(len(bank)) if d[BANK - LO + i] != bank[i]]
    # collapse to ranges
    rs = []
    for i in bad:
        if rs and i - rs[-1][1] <= 16:
            rs[-1][1] = i
        else:
            rs.append([i, i])
    L(f"[{tag}] VBL {h.vbl()} $5138={h.debug('m $5138 4', 0.3).strip().splitlines()[-1]}")
    L(f"   bank/pattern bytes changed: {len(bad)}  ranges {[(hex(BANK + a), hex(BANK + b)) for a, b in rs[:12]]}")
    top = d[BANK - LO + len(bank):]
    nz = [i for i, x in enumerate(top) if x]
    if nz:
        L(f"   above the pattern (${BANK + len(bank):x}..): first non-zero ${BANK + len(bank) + nz[0]:x}, last ${BANK + len(bank) + nz[-1]:x}, {len(nz)} non-zero bytes")
    dumps.append((tag, d))


try:
    # game entry
    f = h.R / "e.txt"
    f.write_text(f"savebin {h.R / 'd_entry.bin'} ${LO:x} ${HI - LO:x}\n")
    h.cmd(f"hatari-debug b pc = $3104 :trace :once :file {f}")
    time.sleep(25)
    if (h.R / "d_entry.bin").exists():
        shutil.copy(h.R / "d_entry.bin", out / "entry.bin")
        d = (out / "entry.bin").read_bytes()
        bad = [i for i in range(len(bank)) if d[BANK - LO + i] != bank[i]]
        L(f"[entry $3104] bank/pattern bytes changed: {len(bad)}")
        dumps.append(("entry", d))
    dump("logo")
    ref = ROOT / "work" / "ref" / "mode_select.png"
    for _ in range(60):
        h.cmd("hatari-event keypress 57")
        time.sleep(5)
        if h.screen_matches(ref, (280, 350, 560, 420)):
            break
    else:
        raise RuntimeError("never reached the M/J/K screen")
    dump("mjk")
    for _ in range(5):
        time.sleep(3)
        h.cmd("hatari-event keypress 50")
        time.sleep(5)
        if not h.screen_matches(ref, (280, 350, 560, 420)):
            break
    time.sleep(8)
    dump("hall")
    h.goto(554, 105); h.click(); time.sleep(15)
    dump("personnel")
    h.goto(389, 140); h.click(); time.sleep(12)
    dump("hall2")
    h.goto(414, 185); h.click(); time.sleep(25)
    dump("map")
    h.goto(150, 280); h.key("space"); time.sleep(18)
    dump("island")
    h.goto(230, 410); h.click(); time.sleep(15)
    dump("objectives")
    boss = ROOT / "work/ref/boss_thumbs.png"
    for _ in range(6):
        h.goto(140, 415); h.click(); time.sleep(8)
        if h.screen_matches(boss, (590, 60, 740, 125)):
            break
    dump("boss")
    h.goto(625, 92); h.click(); time.sleep(40)
    for _ in range(12):
        if h.peekw(0x6220) == 0xD and h.peekw(0x700A) == 2:
            break
        time.sleep(5)
    time.sleep(15)
    dump("3d")
    h.key("F5"); time.sleep(20)
    dump("f5map")
    time.sleep(10)
    dump("f5map2")
    # union of changes over all dumps above the bank end
    base = dumps[0][1]
    ch = set()
    for tag, d in dumps[1:]:
        for i in range(BANK - LO + len(bank), HI - LO):
            if d[i] != base[i]:
                ch.add(i)
    if ch:
        L(f"bytes above ${BANK + len(bank):x} that differ from the entry dump in any later dump: {len(ch)}, lowest ${LO + min(ch):x}, highest ${LO + max(ch):x}")
    nzall = [i for i in range(BANK - LO + len(bank), HI - LO) if any(d[i] for _, d in dumps)]
    if nzall:
        L(f"non-zero in any dump above the pattern: lowest ${LO + nzall[0]:x}")
except Exception as e:
    import traceback
    L("EXC", repr(e)); L(traceback.format_exc())
    try:
        shutil.copy(h.shot(), out / "exc.png")
    except Exception:
        pass
finally:
    h.close()
    (ROOT / "work" / "asn_mus" / f"{name}.txt").write_text("\n".join(log) + "\n")
