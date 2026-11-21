#!/usr/bin/env python3
"""Where HAGA and its swap area are on a given machine/RAM size, and whether the bank survives there (boot to the logo, dump all ST RAM, find the string 'HAGA rulez!'
at HAGA+$30f4, read the record HAGA+$94 {swap start.l, count.w}, compare the bank).   usage: haga_loc.py NAME MACHINE TOS MEM_KB"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import bt, asn_live
name, machine, tos, mem = sys.argv[1:5]
h = bt.start(name, machine, tos, mem, game=Path("/tmp/mw2tail/rel/hd/MW2PATCH"))
try:
    t0 = time.time()
    while time.time() - t0 < 400:
        time.sleep(2)
        if int.from_bytes(asn_live.pk(h, 0x5138, 4, 0.3), "big") == 0xBF81E and int.from_bytes(asn_live.pk(h, 0x7626, 2, 0.3), "big") == 1: break
    else: raise SystemExit("tune never started")
    p = h.R / "ram.bin"
    h.debug(f"savebin {p} 0 ${int(mem) * 1024:x}", 6.0)
    ram = p.read_bytes()
    bank = bt.BANKF.read_bytes()
    i = ram.find(b"HAGA rulez!")
    base = i - 0x30F8          # the string is at HAGA+$30f8
    rec = ram[base + 0x94:base + 0x9A]
    start = int.from_bytes(rec[:4], "big"); cnt = int.from_bytes(rec[4:6], "big")
    print(f"{name}: RAM {mem} KB: 'HAGA rulez!' at ${i:x} => HAGA base ${base:x} (phystop - ${int(mem)*1024 - base:x}); record: swap start ${start:x}, count {cnt} (=> {(cnt + 1) * 48} B to ${start + (cnt + 1) * 48:x})")
    bad = bt.diff(ram[bt.BANK:bt.BANK + len(bank)], bank)
    print(f"{name}: bank ${bt.BANK:x}-${bt.BANK+len(bank):x}: {bt.summ(bad)}; swap start {'<' if start < bt.BANK + len(bank) else '>='} bank end ${bt.BANK+len(bank):x}")
finally:
    h.close()
