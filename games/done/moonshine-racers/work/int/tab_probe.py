"""Cold boot BUILD, SPACE to the race, let ~15 passes run, dump the road work RAM $D0000-$E7FFF and the static game tables; print md5s + magic/WPTR/PM.
Compare a build with rd_init (tables built at race load) against one without (tables built by the first road frame)."""
import sys, time, hashlib, struct
sys.path.insert(0, 'tools')
from msr import Moonshine, GAME
build, tag = sys.argv[1], sys.argv[2]
h = Moonshine(machine="ste", memsize_kb=1024, game_dir=GAME / build)
try:
    print("in_race", h.boot_to_race(log=lambda *a: None), "vbl", h.vbl())
    h.keypress(57)
    t0 = time.time()
    while time.time() - t0 < 90:
        time.sleep(3)
        try:
            if h.peekw(0x100e) > 12 and h.peekb(0x1021) == 2 and h.peekw(0x100e) < 60: break
        except Exception: pass
    print("$100e", h.peekw(0x100e), "vbl", h.vbl())
    out = GAME / "work/int" / f"tab_{tag}.bin"
    h.dump(str(out), 0, 0x100000)
    d = out.read_bytes()
    print("dump", len(d))
    print("RDG1 magic:", d[0xd0000:0xd0004], "PM", struct.unpack('>I', d[0xd0004:0xd0008])[0], "WPTR", hex(struct.unpack('>I', d[0xe7040:0xe7044])[0]), "$135a", hex(struct.unpack('>I', d[0x135a:0x135e])[0]), "$1316", d[0x1316:0x1318].hex())
    for nm, lo, hi in (("rd_geom ram $D0000-$DAFFF", 0xd0000, 0xdb000), ("rd_draw ram $DB000-$E7FFF", 0xdb000, 0xe8000), ("$4154-$4724", 0x4154, 0x4724), ("$4ff8-$5bf7", 0x4ff8, 0x5bf8)):
        print(f"{nm:28s} md5 {hashlib.md5(d[lo:hi]).hexdigest()}")
    print("marker", d[0xb2700:0xb2704])
finally:
    h.close()
