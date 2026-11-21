#!/usr/bin/env python3
"""Exp 2: stage 1 = header watch fires at the end of the bank load -> dump bank (load.bin) + regs; stage 2 = first change of the tail byte
$e2b6a afterwards -> regs, 16 instructions of disassembly at pc, stack, dump of the bank (ow1.bin); keep running; later dump at secs.
   usage: watch2.py NAME MACHINE TOS MEM [cpuclock] [secs]"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import bt
name, machine, tos, mem = sys.argv[1:5]
clk = int(sys.argv[5]) if len(sys.argv) > 5 else 0
secs = int(sys.argv[6]) if len(sys.argv) > 6 else 60
h = bt.start(name, machine, tos, mem)
try:
    if clk: h.set_cpuclock(clk)
    bank = bt.BANKF.read_bytes()
    R = h.R
    f2 = R / "f2.txt"
    f2.write_text(f"r\nd pc\nm $15374 128\nsavebin {R}/ow1.bin ${bt.BANK:x} ${len(bank):x}\nsavebin {R}/ow1_full.bin 0 $100000\n")
    f1 = R / "f1.txt"
    f1.write_text(f"r\nsavebin {R}/load.bin ${bt.BANK:x} ${len(bank):x}\nsavebin {R}/load_full.bin 0 $100000\nb ($e2b6a).b ! ($e2b6a).b :trace :once :file {f2}\n")
    h.cmd(f"hatari-debug b ($bb000).l ! ($bb000).l :trace :once :file {f1}")
    t0 = time.time()
    while time.time() - t0 < secs and not (R / "ow1.bin").exists():
        time.sleep(1)
    time.sleep(2)
    print(h.logpath.read_text(errors="replace")[-6000:])
    for tag in ("load", "ow1"):
        p = R / f"{tag}.bin"
        if p.exists():
            print(tag, bt.summ(bt.diff(p.read_bytes(), bank)))
        else:
            print(tag, "no file")
finally:
    h.close()
