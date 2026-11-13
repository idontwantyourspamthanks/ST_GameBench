#!/usr/bin/env python3
"""Cold boots of a build with the Amiga panel (patches/sky2_pnl.s): work/notes/panel.md.

    python3 tools/pnl_cold.py hd     --machine ste|st|megaste|tt [--mem 2048] [--game build/pnl_hd]
    python3 tools/pnl_cold.py floppy --machine ste|st|falcon|tt   [--disk1 build/pnl_fl/HUNTER_disk1.st] [--mem 2048]

Reports: marker, FLAGS, phystop $42e, option byte, SKY_ST, V_PAN, the master's first bytes; day / night / dusk screenshots
(work/shots/panel_cold_<tag>_<machine>_<mem>_*.png) and 10 s of walking.
"""
from __future__ import annotations
import sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import huntvis as hv                      # noqa: E402
import huntvis_cold as hc                 # noqa: E402
from PIL import Image                     # noqa: E402

TAG = {"mem": 0, "pre": ""}


def pandata_ok(h) -> str:
    """The packed panel block still in RAM, byte for byte (the bank tail $AE4E0.. is the free payload RAM proved in loading.md section 5)."""
    bank = (hv.GAME / "build" / "hunter_snd.bin").read_bytes()
    exp = bank[0xAE4E0 - 0x90000:]
    p = h.R / "pandata.bin"
    h.dump(str(p), 0xAE4E0, len(exp))
    got = p.read_bytes()
    return f"PANDATA {len(exp)} B at $ae4e0 intact: {got == exp}"


def state(h):
    v = hv.var(h)
    pan = h.peek(hv.VAR + 15, 1)[0]
    return v, pan


def report(h, tag, machine, sky_expected):
    v, pan = state(h)
    ph = h.peek(0x42E, 4).hex()
    print(f"BOOT {tag} machine={machine} mem={TAG['mem']}K in_game={h.in_game()} MARKER={h.peek(0x8BFF8, 4)!r} FLAGS={h.peek(0x8BFF0, 4).hex()} "
          f"phystop=${ph} memcntlr$424=${h.peek(0x424, 1).hex()} membot$432=${h.peek(0x432, 4).hex()} memtop$436=${h.peek(0x436, 4).hex()} $ff8001=${h.peek(0xFF8001, 1).hex()} cfg={v['cfg']:#04x} SKY_ST=${v['st']:02x} V_PAN={pan:#04x} H={v['H']} pneed={v['pneed']} master[0:8]={h.peek(0x3682c, 8).hex()} "
          f"PANDATA={h.peek(0xAE4E0, 4)!r}", flush=True)
    hv.SHOTS.mkdir(parents=True, exist_ok=True)
    for nm, hour in (("day", 12), ("night", 2), ("dusk", 21)):
        hv.to_hour(h, hour, settle=9)
        out = hv.SHOTS / f"panel_cold_{TAG["pre"]}{tag}_{machine}_{TAG['mem'] // 1024}mb_{nm}.png"
        Image.open(h.shot(str(h.R / "pc.png"))).convert("RGB").crop((96, 58, 736, 458)).save(out)
        v, pan = state(h)
        print(f"  {nm}: palette {hv.fmt(hv.hwpal(h))} level={h.peek(hv.A5 + 0x18c, 2).hex()} H={v['H']} pneed={v['pneed']} V_PAN={pan:#04x} -> {out.name}", flush=True)
    h.hold("Up")
    time.sleep(10)
    h.release("Up")
    time.sleep(1)
    v, pan = state(h)
    print(f"  after 10 s of walking: in_game={h.in_game()} pos={h.peek(0xAB2, 6).hex()} SKY_ST=${v['st']:02x} V_PAN={pan:#04x}; {pandata_ok(h)}", flush=True)
    extras(h)


def extras(h):
    """Release gate: triple-buffering state and pages (as hunttb_cold) and the one-key items (as hunkeys cold)."""
    from collections import Counter
    import hunkeys as K
    cnt = lambda b: int.from_bytes(b, "big")  # noqa: E731
    names = {0x23000: "A", 0x2AD00: "B", 0x81000: "C"}
    st = h.peek(0x8C1B2, 8)
    seen = Counter()
    for _ in range(60):
        b = h.peek(0x94A, 8)
        seen[(names.get(cnt(b[0:4]), hex(cnt(b[0:4]))), names.get(cnt(b[4:8]), hex(cnt(b[4:8]))))] += 1
        time.sleep(0.05)
    print(f"  TB state $8c1b2: {st.hex()} (mode {cnt(st[4:6])}: 1 = on, 2 = off); pages drawn {sorted({k[0] for k in seen})} shown {sorted({k[1] for k in seen})}", flush=True)
    import numpy as np
    K.pad_rows(K.T(h=h), [("h", "keyboard h (medical kit)", 14), ("g", "keyboard g (fuel can)", 15), ("KP_2", "keypad 2 (weapon 1)", 1)])


def harden(h, _orig=hc.harden):
    _orig(h)
    st0 = h._stage

    def stage(s_, record, wait, timeout=120):
        try:
            return st0(s_, record, wait, timeout)
        except RuntimeError:
            import shutil
            out = f"/tmp/pn/fail_{s_}_{int(time.time())}.png"
            try:
                shutil.copy(h.shot(str(h.R / "fail.png")), out)
                print(f"STAGE FAILED {s_}: screenshot {out}; MARKER={h.peek(0x8BFF8, 4)!r} SKY_ST={h.peek(hv.VAR + 1, 1).hex()} V_PAN={h.peek(hv.VAR + 15, 1).hex()} "
                      f"cfg={h.peek(hv.CFG, 1).hex()} $424={h.peek(0x424, 1).hex()} vbl={h.vbl()}", flush=True)
            except Exception as e:  # noqa: BLE001
                print("STAGE FAILED", s_, e, flush=True)
            raise
    h._stage = stage
    at = h.at
    # the HUD crop is the ST panel; with the Amiga panel it differs by design: the 3D loop marker + flips are checked instead
    h.at = lambda stage: h.in_game() if stage == "game" else at(stage)


def main():
    hc.report = report
    hc.harden = harden
    args = sys.argv[1:]
    if "--pre" in args:                      # file-name prefix, e.g. v12_ for the build without the panel patch
        TAG["pre"] = args[args.index("--pre") + 1]
        del args[args.index("--pre"):args.index("--pre") + 2]
    if "--mem" in args:
        TAG["mem"] = int(args[args.index("--mem") + 1])
    else:
        TAG["mem"] = 1024
    sys.argv = [sys.argv[0]] + args
    hc.main()


if __name__ == "__main__":
    main()
