import os, re, struct, sys, time, shutil, gzip, argparse
from collections import Counter
os.environ["HOME"] = "/tmp/msrmus/home"
os.environ["HATARI"] = "/home/ryan/Code/AtariST/hattari/build/src/hatari"
G = "/home/ryan/Code/AtariST/gamebench"; MR = G + "/games/in_progress/moonshine-racers"
sys.path.insert(0, G + "/tools"); sys.path.insert(0, MR + "/tools")
import msr, msrprof
from msr import Moonshine
from stharness import TOS
OUT = "/tmp/msrmus/out"; os.makedirs(OUT, exist_ok=True)
msrprof.LINE = re.compile(r"^\$?([0-9a-f]{6,8})\s.*% \((\d+), (\d+), \d+, \d+\)\s*$", re.I)
W = lambda b, o=0: struct.unpack(">H", b[o:o + 2])[0]
L = lambda b, o=0: struct.unpack(">I", b[o:o + 4])[0]
PCS = {"vbl": 0xd11e, "tick": 0x8c38, "note": 0x8cd2, "flip": 0xd1ca, "pass": 0x7b86}

def mem(h, addr, n):
    n0 = len(h._logtext()); h.cmd(f"hatari-debug m ${addr:x} {n}")
    last = addr + ((n - 1) // 16) * 16; t = time.time(); out = ""
    while time.time() - t < 8:
        time.sleep(0.15); out = h._logtext()[n0:]
        if re.search(rf"^{last:08x}:", out, re.I | re.M):
            time.sleep(0.1); out = h._logtext()[n0:]; break
    b = bytearray()
    for ln in out.splitlines():
        m = re.match(r"\s*([0-9a-fA-F]{8}):\s+((?:[0-9a-fA-F]{2} )*[0-9a-fA-F]{2})(?:  |$)", ln)
        if m and addr <= int(m.group(1), 16) < addr + n: b += bytes.fromhex(m.group(2).replace(" ", ""))
    return bytes(b[:n])

def race_up(h):
    return L(mem(h, 0x23c0, 4)) != 0 and W(mem(h, 0x100e, 2)) > 30 and mem(h, 0x1021, 1)[0] in (1, 2) and mem(h, 0x1024, 1)[0] == 0

def pin(h):
    for _ in range(8): h.cmd("hatari-event mousemove -100 -80"); time.sleep(0.05)
    time.sleep(0.3)
def mv(h, x, y):
    for _ in range(10): h.cmd(f"hatari-event mousemove {x // 10} {y // 10}"); time.sleep(0.05)
    time.sleep(0.3)
def click(h): h.cmd("hatari-event leftdown"); time.sleep(0.3); h.cmd("hatari-event leftup"); time.sleep(0.3)

def dumpram(h, path, n=0x100000):
    if os.path.exists(path): os.unlink(path)
    h.cmd(f"hatari-debug savebin {path} 0 {n}")
    for _ in range(100):
        time.sleep(0.2)
        if os.path.exists(path) and os.path.getsize(path) >= n: break
    time.sleep(0.3)

def window(h, vbls=300, psg=False, pcs=PCS):
    h.debug("b all", 0.3)
    for n, a in pcs.items(): h.cmd(f"hatari-debug b pc = ${a:x} :trace"); time.sleep(0.15)
    time.sleep(0.3)
    v = h.vbl(); start = len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {v + vbls + 5} :trace :once")
    if psg: h.cmd("hatari-debug trace psg_write")
    out = h._wait_removed(start, timeout=900)
    h.cmd("hatari-debug trace none"); h.debug("b all", 0.5)
    return out

def counts(o): return Counter(re.findall(r"pc = \$([0-9a-f]+) :trace", o))

def patched_stats(h):
    b = mem(h, 0xb8f38, 12); r = mem(h, 0xb8f54, 22)
    return dict(nframes=L(b, 0), ngroups=L(b, 4), nticks=L(b, 8), rsn=[W(r, 2 * i) for i in range(11)])

def run_window(h, tag, vbls=500, psg=False, patched=False, log=print):
    s0 = patched_stats(h) if patched else None
    cyc = mem(h, 0x100e, 2)
    o = window(h, vbls, psg=psg)
    s1 = patched_stats(h) if patched else None
    c = counts(o)
    hz = 50 if (mem(h, 0xff820a, 1)[0] & 2) else 60
    v = c['d11e'] or 1
    line = (f"WIN {tag}: vbl {c['d11e']} ({hz}Hz) ticks {c['8c38']} notes {c['8cd2']} flips {c['d1ca']} passes {c['7b86']} | "
            f"per second: steps {c['7b86']*hz/v:.2f} flips {c['d1ca']*hz/v:.2f} ticks {c['8c38']*hz/v:.2f}")
    if patched:
        de = s1['nframes'] - s0['nframes']
        line += f" | extra frames (NFRAMES delta, bracketed outside window) {de}; ngroups {s1['ngroups']-s0['ngroups']} nticks {s1['nticks']-s0['nticks']} rsn_delta {[b-a for a,b in zip(s0['rsn'],s1['rsn'])]}"
    log(line)
    return line, o

def analyze_ym(o):
    fr = -1; writes = []
    for ln in o.splitlines():
        if ln.startswith("\tpc = $d11e"): fr += 1
        elif "ym write data reg=" in ln and fr >= 0:
            m = re.search(r"reg=0x([0-9a-f]+) val=0x([0-9a-f]+)", ln); writes.append((fr, int(m.group(1), 16), int(m.group(2), 16)))
    nfr = fr + 1
    perframe = Counter(f for f, _, _ in writes)
    st = [None] * 16; per = []; wi = 0
    for f in range(nfr):
        while wi < len(writes) and writes[wi][0] == f:
            _, r, v = writes[wi]; st[r] = v; wi += 1
        per.append(tuple(st))
    ev = {}
    for ch in range(3):
        last = None; times = []
        for f, s in enumerate(per):
            if s[2 * ch] is None: continue
            p = (s[2 * ch], s[2 * ch + 1] & 15)
            if last is not None and p != last: times.append(f)
            last = p
        ev["ABC"[ch]] = times
    return dict(frames=nfr, writes=len(writes), frames_with_writes=len(perframe), regs=dict(sorted(Counter(r for _, r, _ in writes).items())), ev=ev, per=per)

def do_profile(h, tag, vbls=200, log=print):
    ramp = f"{OUT}/{tag}_ram.bin"; pf = f"{OUT}/{tag}_prof.txt"
    dumpram(h, ramp)
    if os.path.exists(pf): os.unlink(pf)
    msr.prof(h, vbls, pf)
    return summarize_profile(tag, ramp, pf, vbls, log)

def summarize_profile(tag, ramp, pf, vbls, log=print):
    ram = open(ramp, "rb").read(); prof = msrprof.load(pf)
    frames, tot, bs = msrprof.buckets(ram, prof)
    nv = vbls + 25
    hdr = open(pf).read(400); clk = re.search(r"Cycles/second:\s+(\d+)", hdr)
    cps = int(clk.group(1)) if clk else 8021247
    vbl_cyc = cps / 50
    lines = [f"PROF {tag}: flips {frames} total_cycles {tot} => {tot/nv:.0f} cycles/VBL over ~{nv} VBL (profile cycles/second {cps}; busy {100*tot/nv/vbl_cyc:.1f}% of a 50Hz VBL)"]
    rng = lambda a: ("YMplayer(8bb6-9344)" if 0x8bb6 <= a < 0x9344 else "VBLISR(d11e-d500)" if 0xd11e <= a < 0xd500 else "other")
    agg = Counter()
    for a, (c, n) in prof.items(): agg[rng(a)] += c
    lines.append("  agg: " + ", ".join(f"{k}={v/nv:.0f}/VBL" for k, v in agg.items()))
    for f, (c, calls) in bs[:14]: lines.append(f"  ${f:05x} {c/nv:9.0f} cyc/VBL {100*c/tot:5.1f}%")
    for l in lines: log(l)
    return lines

def boot(h, tmax=1200):
    t0 = time.time()
    while time.time() - t0 < tmax:
        time.sleep(4); v = h.vbl()
        if v > 5000:
            try:
                if race_up(h): return True
            except Exception: pass
            h.keypress(57)
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("build"); ap.add_argument("mode", choices=["fx", "music"]); ap.add_argument("machine"); ap.add_argument("tag")
    ap.add_argument("--clocks", type=int, nargs="*", default=[])   # extra set_cpuclock steps after native (e.g. 8 16)
    ap.add_argument("--vbls", type=int, default=500); ap.add_argument("--nonative", action="store_true")
    a = ap.parse_args()
    patched = a.build != "orig"
    root = MR + "/originals/MOONSHR" if a.build == "orig" else a.build
    LOGF = open(f"{OUT}/{a.tag}.log", "w")
    def log(*x):
        s = " ".join(str(v) for v in x); print(s, flush=True); LOGF.write(s + "\n"); LOGF.flush()
    wd = f"/tmp/msrmus/run_{a.tag}"; shutil.rmtree(wd, ignore_errors=True)
    h = Moonshine(snapshot=None, game_dir=root, machine=a.machine, memsize_kb=1024, workdir=wd, extra=["--joy1", "keys"], sound=True)
    try:
        ok = boot(h); log("boot_to_race", ok, "vbl", h.vbl(), "$1021", mem(h, 0x1021, 1).hex(), "marker", mem(h, 0xb2700, 4))
        h.debug("w $6105 $01", 0.3)
        p = L(mem(h, 0x133a, 4)); h.debug(f"w ${p:x} $00 $1a $00 $00", 0.8); h.debug("w $6105 $01", 0.3)
        t0 = time.time()
        while time.time() - t0 < 600:
            time.sleep(3)
            if mem(h, 0x1024, 1)[0] == 0xff: break
        h.debug("w $6105 $00", 0.3); time.sleep(15)
        log("shop: $1024", mem(h, 0x1024, 1).hex(), "$1021", mem(h, 0x1021, 1).hex(), "$1023", mem(h, 0x1023, 1).hex(), "$102c", mem(h, 0x102c, 2).hex(), "vbl", h.vbl())
        h.shot(f"{OUT}/{a.tag}_shop_before.png")
        if a.mode == "music":
            pin(h); mv(h, 250, 30); click(h); time.sleep(1.5)
            log("after FX click: $1023", mem(h, 0x1023, 1).hex(), "$1021", mem(h, 0x1021, 1).hex())
            h.shot(f"{OUT}/{a.tag}_shop_after.png")
        pin(h); mv(h, 0, 180); log("pointer", mem(h, 0x6106, 4).hex()); click(h); time.sleep(1)
        t0 = time.time(); r2 = False
        while time.time() - t0 < 240:
            time.sleep(4)
            try:
                if mem(h, 0x1024, 1)[0] != 0xff and race_up(h): r2 = True; break
            except Exception: pass
        log("race2:", r2, "$1021", mem(h, 0x1021, 1).hex(), "$1023", mem(h, 0x1023, 1).hex(), "$102c", mem(h, 0x102c, 2).hex(), "$1028", mem(h, 0x1028, 1).hex(), "vbl", h.vbl())
        if not r2: return
        h.debug("w $6105 $01", 0.3); time.sleep(8)
        h.shot(f"{OUT}/{a.tag}_race2.png")
        steps = ([] if a.nonative else [("native", None)]) + [(f"{c}MHz", c) for c in a.clocks]
        for nm, clk in steps:
            if clk: h.set_cpuclock(clk); time.sleep(3)
            h.debug("w $6105 $01", 0.3)
            t = f"{a.tag}_{nm}"
            run_window(h, t + "_counts", a.vbls, patched=patched, log=log)
            l, o = run_window(h, t + "_ym", 300, psg=True, patched=patched, log=log)
            gzip.open(f"{OUT}/{t}_ym.txt.gz", "wt").write(o)
            an = analyze_ym(o)
            log(f"YM {t}: frames {an['frames']} writes {an['writes']} ({an['writes']/max(an['frames'],1):.2f}/VBL) frames_with_writes {an['frames_with_writes']} regs {an['regs']}")
            log(f"YM {t}: tone events A {len(an['ev']['A'])} B {len(an['ev']['B'])} C {len(an['ev']['C'])}; A times {an['ev']['A'][:40]}")
            do_profile(h, t, 200, log=log)
        log("alive", h.proc.poll() is None, "bus/addr errors", len(re.findall("Bus Error|Address Error", h._logtext())))
    finally:
        h.close()

if __name__ == "__main__":
    main()
