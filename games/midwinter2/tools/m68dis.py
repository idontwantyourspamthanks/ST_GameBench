#!/usr/bin/env python3
"""Disassemble 68000 code from a Midwinter 2 RAM dump, with labels and profile data.

    python3 tools/m68dis.py work/dumps/ram_ingame_lobos.bin 3c5e2            # one function
    python3 tools/m68dis.py DUMP 3c5e2 --end 3c700                           # explicit range
    python3 tools/m68dis.py DUMP 3c5e2 --profile work/prof/walking.txt       # + cycles column
    python3 tools/m68dis.py DUMP --xref 6888                                 # who touches $6888
    python3 tools/m68dis.py DUMP --callers 3c5e2                             # call sites

A function runs from its start to the next call target (the same bucketing the
profile tables use), unless --end is given. Labels `sub_XXXXXX` are every
jsr/bsr target found in $4000-$80000. Hardware registers are annotated.
Profile files are `tools/mw2harness.py profile --top 0` output
(lines: `addr pct cycles`).
"""
from __future__ import annotations

import argparse
import bisect
import re
import struct
import sys

import capstone

CODE_LO, CODE_HI = 0x4000, 0x80000

HW = {
    0xFF8201: "VIDEO_BASE_HI", 0xFF8203: "VIDEO_BASE_MID", 0xFF820D: "VIDEO_BASE_LO",
    0xFF8240: "PALETTE", 0xFF8800: "YM_SELECT", 0xFF8802: "YM_DATA",
    0xFF8A00: "BLT_HALFTONE", 0xFF8A20: "BLT_SRC_XINC", 0xFF8A24: "BLT_SRC_ADDR",
    0xFF8A28: "BLT_ENDMASK1", 0xFF8A2E: "BLT_DST_XINC", 0xFF8A32: "BLT_DST_ADDR",
    0xFF8A36: "BLT_XCOUNT", 0xFF8A38: "BLT_YCOUNT", 0xFF8A3A: "BLT_HOP", 0xFF8A3B: "BLT_OP",
    0xFF8A3C: "BLT_CTRL", 0xFFFA01: "MFP_GPIP", 0xFFFA07: "MFP_IERA", 0xFFFA1B: "MFP_TBCR",
    0xFFFA21: "MFP_TBDR", 0xFFFC00: "ACIA_KBD_CTRL", 0xFFFC02: "ACIA_KBD_DATA",
}
# Game variables identified so far (keep in sync with work/notes/vars.md).
VARS = {
    0x6888: "hud_distance_to_objective", 0x7020: "vbl_counter_ui", 0x770C: "vbl_counter_6",
    0x759E: "ikbd_pkt_left", 0x75A0: "ikbd_pkt_state", 0x75A2: "ikbd_pkt_buf",
}

md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_BIG_ENDIAN | capstone.CS_MODE_M68K_000)


def call_targets(ram: bytes) -> list[int]:
    t = set()
    for a in range(CODE_LO, min(CODE_HI, len(ram) - 6), 2):
        op = struct.unpack_from(">H", ram, a)[0]
        if op == 0x4EB9:
            x = struct.unpack_from(">I", ram, a + 2)[0]
        elif op in (0x6100, 0x4EBA):
            x = a + 2 + struct.unpack_from(">h", ram, a + 2)[0]
        elif (op & 0xFF00) == 0x6100 and (op & 0xFF) not in (0, 0xFF):
            x = a + 2 + struct.unpack_from(">b", ram, a + 1)[0]
        else:
            continue
        if CODE_LO <= x < CODE_HI and x % 2 == 0:
            t.add(x)
    return sorted(t)


def annotate(op_str: str, labels: set[int]) -> str:
    notes = []
    for m in re.finditer(r"\$([0-9a-f]+)", op_str):
        v = int(m.group(1), 16)
        v24 = v & 0xFFFFFF
        if v24 in HW:
            notes.append(HW[v24])
        elif v in VARS:
            notes.append(VARS[v])
        elif v in labels:
            notes.append(f"sub_{v:06x}")
    return ("  ; " + ", ".join(notes)) if notes else ""


def load_profile(path: str) -> dict[int, int]:
    prof = {}
    for line in open(path):
        m = re.match(r"\s*(?:0x)?([0-9a-f]+)\s+[\d.]+%\s+(\d+)", line)
        if m:
            prof[int(m.group(1), 16)] = int(m.group(2))
    return prof


def disasm(ram, start, end, labels, prof):
    total = sum(prof.values()) or 1
    fn_cycles = 0
    out = []
    a = start
    while a < end:
        ins = next(md.disasm(ram[a:a + 10], a), None)
        if ins is None:
            out.append(f"{a:06x}: dc.w ${struct.unpack_from('>H', ram, a)[0]:04x}")
            a += 2
            continue
        if a in labels and a != start:
            out.append(f"\nsub_{a:06x}:")
        cyc = prof.get(a, 0)
        fn_cycles += cyc
        pc = f"{100 * cyc / total:6.2f}%" if prof else ""
        out.append(f"{a:06x}: {pc} {ins.bytes.hex():<20} {ins.mnemonic:<8} {ins.op_str}"
                   f"{annotate(ins.op_str, labels)}")
        a += ins.size
    head = f"sub_{start:06x}:" + (f"   ; {100 * fn_cycles / total:.2f}% of profiled cycles" if prof else "")
    return head + "\n" + "\n".join(out)


def xrefs(ram, target):
    pat = struct.pack(">H", target & 0xFFFF)
    hits = []
    for m in re.finditer(re.escape(pat), ram[CODE_LO:CODE_HI]):
        a = CODE_LO + m.start()
        for back in (2, 4, 6):
            s = a - back
            ins = next(md.disasm(ram[s:s + 10], s), None)
            if ins and ins.size >= back + 2 and re.search(rf"\${target:x}\b", ins.op_str):
                hits.append(f"{s:06x}: {ins.mnemonic} {ins.op_str}")
                break
    return hits


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dump")
    ap.add_argument("start", nargs="?", type=lambda s: int(s, 16))
    ap.add_argument("--end", type=lambda s: int(s, 16))
    ap.add_argument("--profile")
    ap.add_argument("--xref", type=lambda s: int(s, 16))
    ap.add_argument("--callers", type=lambda s: int(s, 16))
    a = ap.parse_args(argv)
    ram = open(a.dump, "rb").read()
    targets = call_targets(ram)
    labels = set(targets)
    if a.xref is not None:
        print("\n".join(xrefs(ram, a.xref)))
        return 0
    if a.callers is not None:
        print("\n".join(h for h in xrefs(ram, a.callers)
                        if h.split(": ", 1)[1].startswith(("jsr", "bsr", "jmp", "bra"))))
        for s in range(CODE_LO, CODE_HI, 2):     # pc-relative bsr/jsr
            op = struct.unpack_from(">H", ram, s)[0]
            if op in (0x6100, 0x4EBA) and s + 2 + struct.unpack_from(">h", ram, s + 2)[0] == a.callers:
                print(f"{s:06x}: {'bsr.w' if op == 0x6100 else 'jsr (pc)'} ${a.callers:x}")
            elif (op & 0xFF00) == 0x6100 and (op & 0xFF) not in (0, 0xFF) \
                    and s + 2 + struct.unpack_from(">b", ram, s + 1)[0] == a.callers:
                print(f"{s:06x}: bsr.b ${a.callers:x}")
        return 0
    if a.start is None:
        ap.error("start address required")
    end = a.end
    if end is None:
        i = bisect.bisect_right(targets, a.start)
        end = targets[i] if i < len(targets) else a.start + 0x200
    prof = load_profile(a.profile) if a.profile else {}
    print(disasm(ram, a.start, end, labels, prof))
    return 0


if __name__ == "__main__":
    sys.exit(main())
