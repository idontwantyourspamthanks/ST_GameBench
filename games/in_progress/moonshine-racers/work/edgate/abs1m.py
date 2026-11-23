#!/usr/bin/env python3
"""Track editor / campaigns: the 1 MB check (HD build, one machine; design section 15.9).
   work/edgate/env7.sh python3 work/edgate/abs1m.py --machine ste [--build DIR] [--ref DIR]
  1. static: RUNME.TOS of the new build against the shipped v1.1 RUNME.TOS: where they differ (expected: only inside cp_title's blob, the hook blobs of cp_fetch / cp_td and the trampoline's
     own core / site tables); HAGA, MS1, MS2, MSR_S1.FIC identical;
  2. cold boot at 1 MB with `--trace gemdos`: marker MSPO, IB+4 = 0 (gate closed); EXACTLY ONE campaign site is patched, cp_welcome's $7c04 (`jmp $B9F0C.l`, the WELCOME PARTNERS key wait:
     the screen says `2 MB: CAMPAIGNS + TRACK EDITOR`), the other eight hold the stock bytes; execution breakpoints, armed as soon as the payload is in RAM, cover every byte of cp_title's
     blob EXCEPT the 1 MB path (the table entry of e3, e3 up to its 2 MB branch, its two exits, the text call shared with the 2 MB hint, hint1mb): none may fire, and hint1mb must run
     (the line was drawn); F10 on the title starts the game like any key, a race runs; no GEMDOS call ever names MSEDIT.OVL."""
import argparse, sys, os, re, subprocess, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
os.environ.setdefault("CG_LOGS", str(HERE / "logs7"))
sys.path.insert(0, str(HERE.parent / "campgate"))
from cg import *
import msrpatch as P

ap = argparse.ArgumentParser(); ap.add_argument("--machine", default="ste"); ap.add_argument("--build", default=os.environ.get("ED_BUILD", "/tmp/msred7/hd")); ap.add_argument("--ref", default="/tmp/msred7/v11/MOONSHR")
a = ap.parse_args()
tag = f"abs1m_{ {'ste': 'ste', 'megaste': 'mste', 'st': 'st', 'megast': 'mst'}[a.machine] }"
logopen(tag)
STOCK = {0x72c4: "4eb9000076f4", 0x77da: "41f900058c004eb90000d6fa", 0xfda2: "41f900058c00", 0x731e: "0c40000f6408", 0x7252: "4eb9000073b8", 0x74fe: "4fef000e6106", 0x8418: "610644fc00ff", 0x7926: "4eb90000edea"}
WELC = (0x7c04, "4a3860ff67f8", "4ef9000b9f0c")                       # cp_welcome: stock bytes, the jump to cp_title's e3
new, ref = (Path(a.build) / "RUNME.TOS").read_bytes(), (Path(a.ref) / "RUNME.TOS").read_bytes()
pt = next(p for p in P.load_patches() if p.name == "cp_title")
blob = [f for f in P.footprint(pt) if f[2] == "blob"][0]
EXTRA = [f for n in ("cp_fetch", "cp_td") for f in P.footprint(next(p for p in P.load_patches() if p.name == n)) if f[2] == "blob"]

def listing():
    """cp_title's blob assembled as msrpatch.py does, with a listing: {global label: address} and the address of the first instruction at / behind a source line"""
    org, lines = next(s for s in pt.segments if s[0] != pt.site)
    common = "".join(f"{k}\tequ\t${v:x}\n" for k, v in P.CP_EQUS.items()) + "FLOPPY\tequ\t0\n"
    src = f"IB\tequ\t${P.IB:x}\nTABLE\tequ\t${P.TABLE:x}\n{common}" + "\n".join(pt.preamble) + f"\n\torg\t${org:x}\n" + "\n".join(lines) + "\n"
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "s.s").write_text(src)
        r_ = subprocess.run([P.VASM, "-Fbin", "-m68000", "-quiet", "-L", f"{td}/s.lst", "-o", f"{td}/s.bin", f"{td}/s.s"], capture_output=True, text=True)
        if r_.returncode: raise SystemExit(r_.stderr)
        lst = (Path(td) / "s.lst").read_text().splitlines()
    sym = {m.group(1): int(m.group(2), 16) for l in lst for m in [re.match(r"^(\w+)\s+A:([0-9A-F]{8})", l)] if m}
    def at(text):
        """address of the first code byte at or behind the listing line that holds `text`"""
        for i, l in enumerate(lst):
            if text in l:
                for l2 in lst[i:]:
                    m = re.match(r"^00:([0-9A-F]{8}) [0-9A-F]+", l2)
                    if m: return int(m.group(1), 16)
    return sym, at
sym, at = listing()
g2, key = at(".g2:"), at(".key:")
allowed = [(0xb9f0c, 0xb9f12), (sym["e3"], g2), (key, sym["hint"]), (sym["hintdr"], at("; ---- floppy title screen"))]
forbidden = []; lo = blob[0]
for a0, a1 in allowed:
    if lo < a0: forbidden.append((lo, a0))
    lo = a1
if lo < blob[1]: forbidden.append((lo, blob[1]))
log(f"cp_title blob ${blob[0]:x}-${blob[1] - 1:x}; the 1 MB path: " + ", ".join(f"${x:x}-${y - 1:x}" for x, y in allowed) + f" (e3 ${sym['e3']:x}, its 2 MB branch ${g2:x}, exits ${key:x}, hintdr ${sym['hintdr']:x}, hint1mb ${sym['hint1mb']:x})")
log("execution breakpoints on: " + ", ".join(f"${x:x}-${y - 1:x}" for x, y in forbidden))

anchor = new.find(bytes.fromhex("4ef9000b9f18"))                      # cp_title's first bytes (jmp e1.l at $B9F18 behind the four-entry jump table) = address $B9F00 in the file
diffs = [i for i in range(min(len(new), len(ref))) if new[i] != ref[i]]
addrs = [i - anchor + 0xb9f00 for i in diffs]
lo_, hi_ = (addrs[0], addrs[-1]) if diffs else (0, 0)
outside = [x for x in addrs if not (blob[0] <= x < blob[1] or P.IB <= x < P.TABLE_END or any(f[0] <= x < f[1] for f in EXTRA))]
log(f"== {tag}: RUNME.TOS new {len(new)} B, v1.1 {len(ref)} B; {len(diffs)} differing bytes, payload addresses ${lo_:x}..${hi_:x}")
log(f"differing bytes outside cp_title's blob, the cp_fetch / cp_td hook blobs and the trampoline (core + site tables, ${P.IB:x}-${P.TABLE_END - 1:x}): {len(outside)}")
check("RUNME.TOS differs from v1.1 only inside cp_title's blob, the cp_fetch / cp_td hook blobs and the trampoline's own core / site tables", len(new) == len(ref) and diffs and not outside)
for f in ("HAGA", "FILES/MS1", "FILES/MS2", "FILES/MSR_S1.FIC"):
    check(f"{f} identical to v1.1", (Path(a.build) / f).read_bytes() == (Path(a.ref) / f).read_bytes())
r = Run("hd", a.machine, 1024, tag, build=a.build, sound=True, extra_args=["--trace", "gemdos"])
try:
    r.ff(True); t0 = time.time()
    while time.time() - t0 < 300 and r.mem(0xb2700, 4) != b"MSPO": time.sleep(0.2)
    r.ff(False)
    check("the payload is in RAM (marker MSPO) before the game starts", r.mem(0xb2700, 4) == b"MSPO", f"vbl {r.vbl()}")
    for x, y in forbidden: r.h.cmd(f"hatari-debug b pc >= ${x:x} && pc < ${y:x} :trace"); time.sleep(0.3)
    r.h.cmd(f"hatari-debug b pc = ${sym['hint1mb']:x} :trace"); time.sleep(0.3); n0 = len(r.h._logtext())
    ok = r.boot_title(); log(f"title reached: {ok} vbl {r.vbl()}"); check("title reached", ok)
    mk = r.mem(0xb2700, 5); st = {ad: r.mem(ad, len(o) // 2).hex() for ad, o in STOCK.items()}; w = r.mem(WELC[0], 6).hex()
    log(f"marker {mk[:4]} IB+4 {mk[4]:#x} $42e {r.l(0x42e):#x} sites {st} $7c04 {w}")
    check("marker MSPO, gate closed (IB+4 = 0)", mk[:4] == b"MSPO" and mk[4] == 0)
    check("exactly one campaign site is patched at 1 MB: $7c04 = jmp $B9F0C.l (cp_welcome); the other eight (incl. cp_td's $7926) hold the stock bytes", w == WELC[2] and all(st[ad] == o for ad, o in STOCK.items()))
    r.h.cmd("hatari-event keypress 0x44"); time.sleep(4)                  # F10 at the title
    res = r.wait_race(tmo=300)
    check("F10 on the title starts the game like any key: race 1 (stock block at $58c00)", res is not None and res[2] >> 8 == 0x58c, f"{res}")
    r.poke(0x6105, 0x01); time.sleep(20); p = r.w(0x5ff8); r.poke(0x6105, 0x00)
    check("the race runs", p > 100, f"$5ff8 {p}")
    t = r.h._logtext(); tl = t[n0:]
    nh = tl.count(f"pc = ${sym['hint1mb']:x} :trace")
    nf = sum(tl.count(f"pc >= ${x:x} && pc < ${y:x} :trace") for x, y in forbidden)
    check(f"the 1 MB line was drawn: hint1mb ran ({nh} time(s): once per showing of the WELCOME PARTNERS screen)", nh >= 1)
    check("no instruction of cp_title's blob outside the 1 MB path was executed (welcome screen, title, F10, race): no campaign menu, no file reader, no editor loader", nf == 0, f"{nf} hits")
    check("no GEMDOS call names MSEDIT.OVL or MSTRACKS.TRK", "MSEDIT" not in t.upper() and "MSTRACKS" not in t.upper(), f"GEMDOS trace lines: {t.count('GEMDOS')}")
    log(f"Bus/Address error lines: {r.errlines()}")
except Exception:
    import traceback; log("EXCEPTION", traceback.format_exc()); FAILS.append("exception")
finally:
    r.close()
log(f"RESULT {tag}: {'ALL CHECKS PASS' if not FAILS else 'FAILED: ' + ', '.join(FAILS)}")
