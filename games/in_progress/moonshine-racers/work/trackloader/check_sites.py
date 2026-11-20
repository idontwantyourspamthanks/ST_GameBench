#!/usr/bin/env python3
"""check_sites.py DUMP.bin [...]: the stage-2 patch sites' original bytes in the RAM of the PATCHED build (race, cold boot dump) vs the stock race dump,
and which shipped patch sites lie near them.  Prints the proposed new bytes (hook addresses are the scratch ones of trkhook.s)."""
import re, sys, glob, struct
G = '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers'
stock = open(f'{G}/work/dumps/ram_race_start.bin', 'rb').read()
SITES = [("A $72c4 wrap the whole race (jsr $76f4)", 0x72c4, 6, bytes.fromhex("4eb9") + struct.pack('>I', 0x100000)),
         ("B $77da track-block fetch (lea $58c00 / jsr $d6fa)", 0x77da, 12, bytes.fromhex("4ef9") + struct.pack('>I', 0x100100) + bytes.fromhex("4e714e714e71")),
         ("C $fda2 stream base pointer (lea $58c00)  [blocks > 6144 B / zero copy]", 0xfda2, 6, bytes.fromhex("2079") + struct.pack('>I', 0x100f10)),
         ("D $731e campaign end test (cmpi.w #$f,d0 / bcc.b $732c)  [count < 15]", 0x731e, 6, bytes.fromhex("4ef9") + struct.pack('>I', 0x100200))]
for dump in sys.argv[1:]:
    d = open(dump, 'rb').read()
    print("==", dump)
    for name, a, n, new in SITES:
        print(f"  {name}: patched RAM {d[a:a+n].hex()}  stock {stock[a:a+n].hex()}  {'SAME' if d[a:a+n] == stock[a:a+n] else 'DIFF'}  -> new {new.hex()}")
sites = []
for f in sorted(glob.glob(f'{G}/patches/*.s')):
    t = open(f).read(3000)
    for m in re.finditer(r'^; site: (.*)$', t, re.M):
        for tok in re.findall(r'\$([0-9a-fA-F]+)', m.group(1)):
            sites.append((int(tok, 16), f.split('/')[-1]))
near = [(hex(a), f) for a, f in sites if 0x72b0 <= a <= 0x7330 or 0x77c0 <= a <= 0x77f0 or 0xfd90 <= a <= 0xfdb0]
print("shipped patch sites within the neighbourhood of the three sites:", near or "none")
