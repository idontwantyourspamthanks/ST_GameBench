#!/usr/bin/env python3
"""Scan a 68000 program for ST-machine-specific hardware access (the "machine checklist" up front).

    python3 tools/hwscan.py DUMP --range af40-21100            # RAM dump (file offset = address), code in $af40-$21100
    python3 tools/hwscan.py DUMP --range 1770-7b380 --min warn # hide the harmless registers
    python3 tools/hwscan.py DEMO.TOS --base ad96               # GEMDOS program, relocated to $ad96 (default $10000)
    python3 tools/hwscan.py DUMP --range 4000-20000 --seed 5e2a --no-ptr --hide-low
    python3 tools/hwscan.py BLOB_IMAGE --range b9500-b9770 --seed b9500   # an assembled patch blob placed at its address

Every finding is one line: address, confidence (H/L), R/W, level (crit/warn/info), the instruction, the
register(s) it hits, the register base it came through, and a one-line risk note. Levels:

    crit  bus-errors (or is absent / differs) on at least one of ST, Mega ST, STE, Mega STE, TT, Falcon
          unless guarded: YM mirrors $ff8804/06 and odd addresses, blitter, DMA sound, enhanced joystick ports,
          the Mega STE cache $ff8e21, RTC, TT/Falcon-only video, SCSI, DSP, MFP2, SCC
    warn  works everywhere but is machine- or TOS-shared: sync mode $ff820a (50/60 Hz), STE video regs, MFP
          timers and interrupt masks, FDC/DMA, writes to the exception / interrupt vectors $8-$3ff
    info  harmless on every machine (palette, screen base, shift mode, YM $ff8800/02, IKBD/MIDI ACIA ...)

What it finds: absolute (.w sign-extended, .l) operands, `movep` (every byte it touches, so the YM mirrors
$ff8804/06 show), `d(An)` / `(An)` / `(An)+` / `-(An)` / `d(An,Xn)` where An is provably a constant: a forward
constant-propagation over the code (lea / movea #imm / move.l #imm / suba.l An,An / moveq / addq / adda /
copies, merged over branches, forgotten at calls and traps), pointer loads (`lea $ff8800,a0`, `move.l
#$ffff8a00,...`, `movea.w #$8800,a0` = kind P, level of the register they point at), and stores to vectors.
Spans (`movem.l d0-d4,$ffff8250` runs on into $ff8260/62) are reported with every register they touch.

Code finding (data decoded as code is the usual source of false hits): recursive descent from the range
start, the dump's own vector table ($8-$3fc longs inside the range), `--seed` addresses, and every branch /
call / jump-table target of accepted code. A path is accepted only if it decodes cleanly to a terminator
(rts, rte, rtr, bra, jmp) inside the range, with no illegal opcode, no zero word, no line-F, no branch out of
the range. Confidence H = reached that way. The gaps are then swept for unreached code: a clean run of at
least 6 instructions ending in a terminator is accepted as confidence L (reached by no known caller: a jump
through a table of pointers, an interrupt installed by a routine this scan did not reach). L lines are
marked `?`; `--hide-low` drops them. Code the scan cannot reach and cannot recognise is not seen: a clean
result is not proof (the summary prints how many bytes of the range were taken as code).

Limits: the constant tracking is per path (merge = equal values), a register passed through a call or kept
in memory is not followed (the pointer load P line still shows the base was taken); self-modified or
packed code is seen as it is in the dump; the 68000 flavour only (no 68010+ opcodes).
"""
from __future__ import annotations

import argparse
import os
import re
import signal
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m68dis  # noqa: E402  (the shared capstone 68000 disassembler)

md = m68dis.md
M32 = 0xFFFFFFFF
LEVELS = {"info": 0, "warn": 1, "crit": 2}
LEVEL_NAME = {v: k for k, v in LEVELS.items()}
MINRUN_LOW = 6           # a gap run needs this many new instructions to count as code
MAXWALK = 4096           # instructions per path

# ----------------------------------------------------------------------------------------------------
# Hardware map: (lo, hi, group, machines, level, one-line risk note); addresses are 24-bit, hi inclusive.
# ----------------------------------------------------------------------------------------------------
I, W, C = LEVELS["info"], LEVELS["warn"], LEVELS["crit"]
REGIONS = [
    (0xFF8000, 0xFF8007, "MMU_CONFIG", "all, differs", W, "memory/bus controller ($ff8001 memconfig, $ff8006 Falcon monitor type): differs per machine, never write it"),
    (0xFF8200, 0xFF8203, "VIDEO_BASE", "all", I, "screen base high/mid (TT/Falcon follow the live register at once; an ST/STE latches per frame)"),
    (0xFF8204, 0xFF8209, "VIDEO_COUNTER", "all", I, "video address counter, read-only: used for sync/raster tricks; timing differs per machine"),
    (0xFF820A, 0xFF820B, "SYNC_MODE", "all", W, "$ff820a bit 1 = 50/60 Hz: a game that tests it may refuse 60 Hz or misrun (Populous 2 PAL check)"),
    (0xFF820C, 0xFF820D, "VIDEO_BASE_LO", "STE+", W, "STE/Mega STE/TT/Falcon register: not on an ST/Mega ST"),
    (0xFF820E, 0xFF820F, "LINE_OFFSET", "STE+", W, "STE line offset: not on an ST/Mega ST"),
    (0xFF8210, 0xFF8211, "LINE_WIDTH", "STE+", W, "STE/TT line width: not on an ST/Mega ST"),
    (0xFF8212, 0xFF823F, "VIDEO_OTHER", "TT/Falcon", C, "TT/Falcon-only video register"),
    (0xFF8240, 0xFF825F, "PALETTE", "all", I, "ST palette (STE: 4 bits, LSB extra): all machines; a movem past $ff825e runs into the shift mode"),
    (0xFF8260, 0xFF8261, "SHIFT_MODE", "all", I, "resolution: TT/Falcon map the ST modes; a monochrome ST can only run mode 2"),
    (0xFF8262, 0xFF8263, "TT_SHIFT_MODE", "TT", C, "TT shift mode: on the TT its high byte selects TT-low/TT-high; absent on ST/STE"),
    (0xFF8264, 0xFF8265, "HSCROLL", "STE+", W, "STE fine scroll: not on an ST/Mega ST"),
    (0xFF8266, 0xFF8267, "FALCON_SPSHIFT", "Falcon", C, "Falcon-only video shift register"),
    (0xFF8280, 0xFF82C3, "FALCON_VIDEO", "Falcon", C, "Falcon-only video timing registers"),
    (0xFF8400, 0xFF85FF, "TT_PALETTE", "TT", C, "TT-only 256-colour palette"),
    (0xFF8604, 0xFF8605, "DMA_DATA", "all", W, "FDC/HDC data port: the game drives the disk itself; breaks HD/GEMDOS loading and differs on TT/Falcon"),
    (0xFF8606, 0xFF8607, "DMA_MODE", "all", W, "DMA status/mode: same, own disk routines"),
    (0xFF8608, 0xFF860D, "DMA_ADDRESS", "all", W, "DMA address pointer: own disk routines"),
    (0xFF860E, 0xFF860F, "DMA_DENSITY", "MSTE/Falcon", C, "floppy density/HD control: not on ST/STE/TT"),
    (0xFF8700, 0xFF8715, "FALCON_SCSI_DMA", "Falcon", C, "Falcon-only SCSI DMA"),
    (0xFF8780, 0xFF878F, "SCSI_NCR5380", "TT/Falcon", C, "TT/Falcon-only SCSI controller"),
    (0xFF8800, 0xFF8801, "YM_SELECT", "all", I, "YM2149 register select/read: plain access, fine everywhere"),
    (0xFF8802, 0xFF8803, "YM_DATA", "all", I, "YM2149 data write: plain access, fine everywhere"),
    (0xFF8804, 0xFF8807, "YM_MIRROR", "ST/STE decode, Falcon bus error", C, "YM mirror $ff8804/06 (movep.l or a long store): bus error on a Falcon (fal_ym / pop_fal_ym)"),
    (0xFF8808, 0xFF88FF, "YM_MIRROR_FAR", "ST/STE decode, Falcon bus error", C, "YM mirror beyond $ff8807: bus error on a Falcon"),
    (0xFF8900, 0xFF8925, "DMA_SOUND", "STE+", C, "STE DMA sound / microwire: bus error on an ST/Mega ST; Falcon redefines the block"),
    (0xFF8930, 0xFF895F, "FALCON_SOUND", "Falcon", C, "Falcon-only sound matrix / codec"),
    (0xFF8960, 0xFF8963, "NVRAM_RTC", "TT/Falcon", C, "TT/Falcon NVRAM/RTC"),
    (0xFF8A00, 0xFF8A3F, "BLITTER", "STE/MSTE/Falcon/Mega ST (not plain ST, TT)", C, "blitter: bus error on a plain ST and on a TT; probe it; a HOG burst starves the IKBD ACIA"),
    (0xFF8C80, 0xFF8C87, "SCC", "MSTE/TT/Falcon", C, "SCC serial: Mega STE/TT/Falcon only"),
    (0xFF8E00, 0xFF8E1F, "SCU_VME", "MSTE/TT", C, "system control / VME mask: Mega STE and TT only"),
    (0xFF8E20, 0xFF8E21, "MSTE_CACHE", "MSTE", C, "Mega STE CPU speed/cache ($ff8e21): bus error on every other machine"),
    (0xFF9200, 0xFF9203, "JOY_PORTS", "STE+", C, "enhanced joystick ports $ff9200/02: absent on ST/Mega ST/TT, probe and keep a $ff9202-less path"),
    (0xFF9210, 0xFF922F, "PADDLE_LIGHTGUN", "STE+", C, "STE paddle / light-gun ports: absent on ST/Mega ST/TT"),
    (0xFF9800, 0xFF9BFF, "FALCON_PALETTE", "Falcon", C, "Falcon-only 24-bit palette"),
    (0xFFA200, 0xFFA207, "DSP_HOST", "Falcon", C, "Falcon-only DSP host port"),
    (0xFFFA00, 0xFFFA06, "MFP_GPIP", "all", I, "MFP GPIP/AER/DDR: line wiring differs (blitter-done, mono detect, FDC/HDC)"),
    (0xFFFA07, 0xFFFA18, "MFP_IRQ", "all", W, "MFP interrupt enable/pending/mask: leave TOS's bits alone and restore them on exit"),
    (0xFFFA19, 0xFFFA26, "MFP_TIMER", "all", W, "MFP timers: C = TOS 200 Hz tick, D = RS-232, B = HBL; changing them skews TOS timing"),
    (0xFFFA27, 0xFFFA3F, "MFP_USART", "all", I, "MFP RS-232 USART"),
    (0xFFFA80, 0xFFFABF, "MFP2_TT", "TT", C, "TT-only second MFP"),
    (0xFFFC00, 0xFFFC03, "ACIA_IKBD", "all", I, "keyboard/mouse ACIA: shared with TOS's handler; blitter HOG bursts and long IRQ-off sections lose bytes"),
    (0xFFFC04, 0xFFFC07, "ACIA_MIDI", "all", I, "MIDI ACIA"),
    (0xFFFC20, 0xFFFC3F, "RTC_MEGA", "Mega ST/Mega STE", C, "Mega RTC: bus error on ST/STE/TT/Falcon (Populous on a TT: `writing $fffffc3b`)"),
]
REGIONS.sort()

NAMES: dict[int, str] = {
    0xFF8201: "VBASE_HI", 0xFF8203: "VBASE_MID", 0xFF8205: "VCNT_HI", 0xFF8207: "VCNT_MID", 0xFF8209: "VCNT_LO",
    0xFF820A: "SYNC", 0xFF820D: "VBASE_LO", 0xFF820E: "LINE_OFS", 0xFF8210: "LINE_WIDTH", 0xFF8260: "SHIFT",
    0xFF8262: "TT_SHIFT", 0xFF8264: "HSCROLL", 0xFF8265: "HSCROLL_PF", 0xFF8266: "SPSHIFT",
    0xFF8604: "DMA_DATA", 0xFF8606: "DMA_MODE", 0xFF8609: "DMA_ADDR_HI", 0xFF860B: "DMA_ADDR_MID", 0xFF860D: "DMA_ADDR_LO",
    0xFF8800: "YM_SELECT", 0xFF8802: "YM_DATA", 0xFF8804: "YM_MIRROR", 0xFF8806: "YM_MIRROR",
    0xFF8901: "SND_CTRL", 0xFF8903: "SND_START_HI", 0xFF8905: "SND_START_MID", 0xFF8907: "SND_START_LO",
    0xFF8909: "SND_CNT_HI", 0xFF890B: "SND_CNT_MID", 0xFF890D: "SND_CNT_LO", 0xFF890F: "SND_END_HI",
    0xFF8911: "SND_END_MID", 0xFF8913: "SND_END_LO", 0xFF8921: "SND_MODE", 0xFF8922: "MW_DATA", 0xFF8924: "MW_MASK",
    0xFF8A20: "BLT_SRC_XINC", 0xFF8A22: "BLT_SRC_YINC", 0xFF8A24: "BLT_SRC_ADDR", 0xFF8A28: "BLT_ENDMASK1",
    0xFF8A2A: "BLT_ENDMASK2", 0xFF8A2C: "BLT_ENDMASK3", 0xFF8A2E: "BLT_DST_XINC", 0xFF8A30: "BLT_DST_YINC",
    0xFF8A32: "BLT_DST_ADDR", 0xFF8A36: "BLT_XCOUNT", 0xFF8A38: "BLT_YCOUNT", 0xFF8A3A: "BLT_HOP",
    0xFF8A3B: "BLT_OP", 0xFF8A3C: "BLT_CTRL", 0xFF8A3D: "BLT_SKEW", 0xFF8E21: "MSTE_CPU_CACHE",
    0xFF9200: "JOY_FIRE", 0xFF9202: "JOY_DIR", 0xFF9210: "PAD0_X", 0xFF9212: "PAD0_Y", 0xFF9214: "PAD1_X",
    0xFF9216: "PAD1_Y", 0xFF9220: "LIGHTPEN_X", 0xFF9222: "LIGHTPEN_Y",
    0xFFFC00: "IKBD_CTRL", 0xFFFC02: "IKBD_DATA", 0xFFFC04: "MIDI_CTRL", 0xFFFC06: "MIDI_DATA",
}
for _i in range(16):
    NAMES[0xFF8240 + 2 * _i] = f"PAL{_i}"
    NAMES[0xFF8A00 + 2 * _i] = f"BLT_HALFTONE{_i}"
for _n, _a in enumerate(("GPIP", "AER", "DDR", "IERA", "IERB", "IPRA", "IPRB", "ISRA", "ISRB", "IMRA", "IMRB", "VR",
                         "TACR", "TBCR", "TCDCR", "TADR", "TBDR", "TCDR", "TDDR", "SCR", "UCR", "RSR", "TSR", "UDR")):
    NAMES[0xFFFA01 + 2 * _n] = "MFP_" + _a

VECTOR_NAMES = {0x08: "bus error", 0x0C: "address error", 0x10: "illegal instruction", 0x14: "divide by zero",
                0x18: "CHK", 0x1C: "TRAPV", 0x20: "privilege", 0x24: "trace", 0x28: "line A", 0x2C: "line F",
                0x60: "spurious", 0x64: "autovector 1", 0x68: "HBL (autovector 2)", 0x6C: "autovector 3",
                0x70: "VBL (autovector 4)", 0x74: "autovector 5", 0x78: "autovector 6", 0x7C: "autovector 7 (NMI)",
                0x100: "MFP GPIP0 (parallel busy)", 0x104: "MFP GPIP1 (DCD)", 0x108: "MFP GPIP2 (CTS)",
                0x10C: "MFP GPIP3 (blitter done)", 0x110: "MFP timer D", 0x114: "MFP timer C", 0x118: "MFP ACIA (IKBD/MIDI)",
                0x11C: "MFP GPIP5 (FDC/HDC)", 0x120: "MFP timer B (HBL counter)", 0x124: "MFP TX error",
                0x128: "MFP TX empty", 0x12C: "MFP RX error", 0x130: "MFP RX full", 0x134: "MFP timer A",
                0x138: "MFP GPIP6 (RI)", 0x13C: "MFP GPIP7 (mono detect)"}
for _n in range(16):
    VECTOR_NAMES[0x80 + 4 * _n] = f"trap #{_n}"


def vector_name(ea: int) -> str:
    base = ea & ~3
    if base in VECTOR_NAMES:
        return VECTOR_NAMES[base]
    if 0x140 <= base < 0x180:
        return "TT MFP2 interrupt"
    return f"vector ${base:x}"


def vec_note(ea: int) -> str:
    n = vector_name(ea)
    if ea & ~3 in (0x8, 0xC):
        return f"writes the {n} vector: a temporary handler around hardware accesses = a guarded probe (check it is restored)"
    if 0x140 <= (ea & ~3) < 0x180:
        return f"writes the {n} vector: the TT's second MFP uses these slots (the game's own use must not collide)"
    return f"writes the {n} vector: replaces TOS's handler; restore it on exit"


def region_of(a24: int):
    for r in REGIONS:
        if r[0] <= a24 <= r[1]:
            return r
    return None


def is_io(ea: int) -> bool:
    return (ea >> 24) in (0, 0xFF) and (ea & 0xFFFFFF) >= 0xFF8000


LONG_REGS = {0xFF8A24: 4, 0xFF8A32: 4}                 # registers wider than a word


def reg_name(a24: int, r):
    """The register a byte belongs to, or None for an unnamed pad byte of a wider access."""
    if a24 in NAMES:
        return NAMES[a24]
    for back in (1, 2, 3):
        b = a24 - back
        if b in NAMES and r[0] <= b and back < LONG_REGS.get(b, 2 if b % 2 == 0 else 1):
            return NAMES[b]
    return None


# ----------------------------------------------------------------------------------------------------
# Decoding and operand parsing
# ----------------------------------------------------------------------------------------------------
class Ins:
    __slots__ = ("a", "size", "mn", "sz", "ops", "text", "raw", "pops", "fl")


def parse_num(s: str) -> int:
    s = s.strip()
    neg = s.startswith("-")
    s = s.lstrip("-")
    v = int(s[1:], 16) if s.startswith("$") else int(s)
    return -v if neg else v


def split_ops(s: str) -> list[str]:
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


NUM = r"-?\$[0-9a-f]+|-?\d+"
RE_D = re.compile(r"^d([0-7])$")
RE_A = re.compile(r"^a([0-7])$")
RE_IMM = re.compile(rf"^#({NUM})$")
RE_ABS = re.compile(r"^(-?\$[0-9a-f]+)\.([wl])$")
RE_IND = re.compile(r"^\(a([0-7])\)$")
RE_POST = re.compile(r"^\(a([0-7])\)\+$")
RE_PRE = re.compile(r"^-\(a([0-7])\)$")
RE_DISP = re.compile(rf"^({NUM})\(a([0-7])\)$")
RE_IDX = re.compile(rf"^(?:({NUM}))?\(a([0-7]), ([ad][0-7])\.([wl])\)$")
RE_PCD = re.compile(r"^(\$[0-9a-f]+)\(pc\)$")
RE_PCI = re.compile(r"^(\$[0-9a-f]+)\(pc, ([ad][0-7])\.([wl])\)$")
RE_LIST = re.compile(r"^[da][0-7](-[da][0-7])?(/[da][0-7](-[da][0-7])?)*$")


def parse_op(s: str):
    m = RE_D.match(s)
    if m:
        return ("d", int(m.group(1)))
    m = RE_A.match(s)
    if m:
        return ("a", int(m.group(1)))
    m = RE_IMM.match(s)
    if m:
        return ("imm", parse_num(m.group(1)))
    m = RE_ABS.match(s)
    if m:
        v = parse_num(m.group(1))
        if m.group(2) == "w":
            v = (v & 0xFFFF) | (0xFFFF0000 if v & 0x8000 else 0)
        return ("abs", v & M32)
    m = RE_IND.match(s)
    if m:
        return ("ind", int(m.group(1)))
    m = RE_POST.match(s)
    if m:
        return ("post", int(m.group(1)))
    m = RE_PRE.match(s)
    if m:
        return ("pre", int(m.group(1)))
    m = RE_DISP.match(s)
    if m:
        return ("disp", int(m.group(2)), parse_num(m.group(1)))
    m = RE_IDX.match(s)
    if m:
        return ("idx", int(m.group(2)), parse_num(m.group(1)) if m.group(1) else 0)
    m = RE_PCD.match(s)
    if m:
        return ("pcd", parse_num(m.group(1)))
    m = RE_PCI.match(s)
    if m:
        return ("pci", parse_num(m.group(1)))
    if RE_LIST.match(s):
        regs = set()
        for part in s.split("/"):
            if "-" in part:
                a, b = part.split("-")
                for n in range(int(a[1]), int(b[1]) + 1):
                    regs.add((a[0], n))
            else:
                regs.add((part[0], int(part[1])))
        return ("list", regs)
    return ("other",)


SIZE_BYTES = {"b": 1, "w": 2, "l": 4}
RE_BCC = re.compile(r"^b(hi|ls|cc|cs|ne|eq|vc|vs|pl|mi|ge|lt|gt|le|hs|lo)$")
RE_DBCC = re.compile(r"^db(t|ra|f|hi|ls|cc|cs|ne|eq|vc|vs|pl|mi|ge|lt|gt|le)$")
RE_SCC = re.compile(r"^s(t|f|hi|ls|cc|cs|ne|eq|vc|vs|pl|mi|ge|lt|gt|le)$")
NOWRITE = {"cmp", "cmpa", "cmpi", "cmpm", "tst", "btst", "chk", "pea", "jmp", "jsr", "bsr", "bra", "movem"}
RMW = {"add", "adda", "addi", "addq", "addx", "sub", "suba", "subi", "subq", "subx", "and", "andi", "or", "ori",
       "eor", "eori", "neg", "negx", "not", "bset", "bclr", "bchg", "tas", "nbcd", "asl", "asr", "lsl", "lsr",
       "rol", "ror", "roxl", "roxr", "abcd", "sbcd", "mulu", "muls", "divu", "divs", "exg", "swap", "ext"}


ONLY_020 = {"bfchg", "bfclr", "bfexts", "bfextu", "bfffo", "bfins", "bfset", "bftst", "cas", "cas2", "cmp2", "chk2",
            "pack", "unpk", "rtd", "extb", "callm", "rtm", "divsl", "divul", "moves", "movec", "bkpt",
            "trapcc", "trapt", "trapf", "traphi", "trapls", "trapcs", "trapne", "trapeq", "trapvc", "trapvs",
            "trappl", "trapmi", "trapge", "traplt", "trapgt", "traple"}


class Scan:
    def __init__(self, mem: bytes, lo: int, hi: int):
        self.mem, self.lo, self.hi = mem, lo, hi
        self.cache: dict[int, Ins | None] = {}
        self.code: dict[int, Ins] = {}
        self.conf: dict[int, str] = {}
        self.entries: set[int] = set()
        self.calls: set[int] = set()
        self.claimed = bytearray(len(mem) + 16)         # bytes covered by accepted instructions

    # --- decode ---------------------------------------------------------------------------------
    def dec(self, a: int):
        if a in self.cache:
            return self.cache[a]
        r = None
        if 0 <= a and a + 2 <= len(self.mem):
            c = next(md.disasm(self.mem[a:a + 10], a, 1), None)
            if c is not None:
                r = Ins()
                r.a, r.size = a, c.size
                r.text = f"{c.mnemonic} {c.op_str}".strip()
                mn, _, sz = c.mnemonic.partition(".")
                r.mn, r.sz = mn, sz or None
                r.ops = split_ops(c.op_str)
                r.pops = [parse_op(o) for o in r.ops]
                r.raw = self.mem[a:a + c.size]
                r.fl = None
            elif a + 2 <= len(self.mem):
                pass
        self.cache[a] = r
        return r

    def inrange(self, a: int) -> bool:
        return self.lo <= a < self.hi and a % 2 == 0

    def plausible(self, ins: Ins) -> bool:
        if ins.mn == "illegal":
            return False
        if ins.mn == "dc":                      # only the line-A calls TOS programs use
            w = struct.unpack(">H", ins.raw[:2])[0]
            return 0xA000 <= w <= 0xA00F
        if ins.raw[:2] == b"\0\0":
            return False
        if "[" in ins.text or "*" in ins.text:           # 68020 memory-indirect / scaled index decoded from data
            return False
        if ins.mn in ONLY_020 or (ins.mn in ("mulu", "muls", "divu", "divs", "link") and ins.sz == "l"):
            return False
        return True

    # --- flow -----------------------------------------------------------------------------------
    def flow(self, ins: Ins):
        """(kind, [(target, hard)], falls, table) for control flow; kind in seq/end/bra/bcc/call."""
        if ins.fl is not None:
            return ins.fl
        mn, ops, p = ins.mn, ins.ops, ins.pops
        tg: list[tuple[int, bool]] = []
        table = None
        falls = True
        kind = "seq"

        def tgt(i):
            q = p[i]
            if q[0] in ("abs", "pcd"):
                return q[1] & M32
            if q[0] == "other" and ops[i].startswith("$"):
                return parse_num(ops[i])
            return None

        if mn in ("rts", "rte", "rtr"):
            kind, falls = "end", False
        elif mn == "bra" or RE_BCC.match(mn):
            t = tgt(0)
            if t is not None:
                tg.append((t, True))
            kind, falls = ("bra", False) if mn == "bra" else ("bcc", True)
        elif RE_DBCC.match(mn):
            t = tgt(1)
            if t is not None:
                tg.append((t, True))
            kind = "bcc"
        elif mn == "bsr":
            t = tgt(0)
            if t is not None:
                tg.append((t, False))
            kind = "call"
        elif mn == "jsr":
            if p and p[0][0] in ("abs", "pcd"):
                tg.append((p[0][1], False))
            elif p and p[0][0] == "pci":
                table = p[0][1]
            kind = "call"
        elif mn == "jmp":
            if p and p[0][0] in ("abs", "pcd"):
                tg.append((p[0][1], False))
            elif p and p[0][0] == "pci":
                table = p[0][1]
            kind, falls = "bra", False
        elif mn in ("trap", "dc"):
            kind = "call"
        ins.fl = (kind, tg, falls, table)
        return ins.fl

    # --- code discovery -----------------------------------------------------------------------------
    def walk(self, seed: int, minlen: int):
        """Decode a path from seed. Returns (path, subseeds, calls) if it ends cleanly, else None."""
        path: list[Ins] = []
        subs: list[int] = []
        calls: list[int] = []
        a = seed
        seen = set()
        while True:
            if a in self.code or a in seen:
                break
            if not self.inrange(a) or len(path) > MAXWALK:
                return None
            ins = self.dec(a)
            if ins is None or not self.plausible(ins):
                return None
            if any(self.claimed[a:a + ins.size]):         # overlaps accepted code at another alignment
                return None
            path.append(ins)
            seen.add(a)
            kind, tg, falls, table = self.flow(ins)
            for t, hard in tg:
                if hard:
                    if not self.inrange(t):
                        return None
                    subs.append(t)
                elif self.inrange(t):
                    subs.append(t)
                    if kind == "call":
                        calls.append(t)
                elif t % 2 or t >= 0x1000000:
                    return None
            if (ins.mn == "move" and ins.sz == "l" and len(ins.pops) == 2 and ins.pops[0][0] == "imm"
                    and ins.pops[1][0] == "abs" and 8 <= ins.pops[1][1] < 0x400 and self.inrange(ins.pops[0][1])):
                subs.append(ins.pops[0][1])                  # move.l #handler,vector
            if table is not None:
                x = table
                for _ in range(128):
                    e = self.dec(x) if self.inrange(x) else None
                    if e is None or e.mn not in ("bra", "jmp"):
                        break
                    subs.append(x)
                    x += e.size
            if not falls:
                break
            a += ins.size
        if len(path) < minlen:
            return path
        return path, subs, calls

    def accept(self, seed: int, conf: str, minlen: int, entry: bool):
        work = [(seed, minlen, entry)]
        n = 0
        while work:
            s, ml, ent = work.pop()
            if s in self.code:
                continue
            r = self.walk(s, ml)
            if r is None or isinstance(r, list):
                continue
            path, subs, calls = r
            for ins in path:
                self.code[ins.a] = ins
                self.conf[ins.a] = conf
                self.claimed[ins.a:ins.a + ins.size] = b"\1" * ins.size
            if ent:
                self.entries.add(s)
            self.calls.update(calls)
            n += len(path)
            work.extend((t, 1, False) for t in subs)
        return n

    def discover(self, seeds: list[int], sweep: bool):
        for s in seeds:
            self.accept(s, "H", 1, True)
        if sweep:
            a = self.lo
            while a < self.hi:
                if a in self.code:
                    a += self.code[a].size
                    continue
                r = self.walk(a, MINRUN_LOW)
                if r is None:
                    a += 2
                elif isinstance(r, list):                # a clean but short run: skip it whole, never re-enter it misaligned
                    a = r[-1].a + r[-1].size if r else a + 2
                else:
                    self.accept(a, "L", MINRUN_LOW, True)

    # --- constant propagation -----------------------------------------------------------------------
    @staticmethod
    def sext16(v: int) -> int:
        v &= 0xFFFF
        return (v | 0xFFFF0000) if v & 0x8000 else v

    def transfer(self, ins: Ins, st: dict):
        mn, sz, p = ins.mn, ins.sz, ins.pops
        if mn in ("jsr", "bsr", "trap", "dc", "stop"):
            return {}
        out = dict(st)
        nb = SIZE_BYTES.get(sz or "w", 2)
        for q in p:                                  # (An)+ / -(An)
            if q[0] in ("post", "pre"):
                k = ("a", q[1])
                if mn == "movem":
                    out.pop(k, None)
                elif k in out:
                    d = nb if q[0] == "post" else -nb
                    out[k] = ((out[k][0] + d) & M32, out[k][1])
        if mn == "movem":
            if len(p) == 2 and p[1][0] == "list":          # memory -> registers
                for k in p[1][1]:
                    out.pop(k, None)
            elif len(p) == 2 and p[1][0] in ("d", "a"):
                out.pop((p[1][0], p[1][1]), None)
            return out
        dst = p[-1] if p else None
        src = p[0] if p else None

        def val(q):
            if q[0] == "imm":
                v = q[1] & M32
                if sz == "w":
                    return self.sext16(v)
                if sz == "b":
                    return (v | 0xFFFFFF00) if v & 0x80 else v & 0xFF
                return v
            if q[0] in ("d", "a"):
                e = st.get((q[0], q[1]))
                return e[0] if e else None
            return None

        def setr(q, v):
            k = (q[0], q[1])
            if v is None:
                out.pop(k, None)
            else:
                out[k] = (v & M32, ins.a)

        if mn == "lea" and dst[0] == "a":
            q = src
            v = None
            if q[0] in ("abs", "pcd"):
                v = q[1]
            elif q[0] == "ind" and ("a", q[1]) in st:
                v = st[("a", q[1])][0]
            elif q[0] == "disp" and ("a", q[1]) in st:
                v = st[("a", q[1])][0] + q[2]
            setr(dst, v)
        elif mn in ("move", "movea") and dst[0] in ("a", "d"):
            v = val(src) if src[0] in ("imm", "d", "a") else None
            if dst[0] == "d" and sz != "l":
                v = None
            setr(dst, v)
        elif mn == "moveq":
            v = src[1] & 0xFF
            setr(dst, (v | 0xFFFFFF00) if v & 0x80 else v)
        elif mn == "clr" and dst[0] == "d":
            setr(dst, 0 if sz == "l" else None)
        elif mn in ("sub", "suba", "eor") and sz == "l" and src == dst and dst[0] in ("a", "d"):
            setr(dst, 0)
        elif mn in ("adda", "suba", "add", "sub", "addq", "subq") and dst[0] in ("a", "d"):
            cur = st.get((dst[0], dst[1]))
            sv = val(src) if src[0] in ("imm", "d", "a") else None
            if dst[0] == "d" and sz != "l":
                setr(dst, None)
            elif cur is None or sv is None:
                setr(dst, None)
            else:
                if mn in ("adda",) and sz == "w" and src[0] != "imm":
                    sv = self.sext16(sv)
                setr(dst, cur[0] + sv if mn in ("adda", "add", "addq") else cur[0] - sv)
        elif mn in ("link",) and p and p[0][0] == "a":
            setr(p[0], None)
        elif mn in ("unlk",) and p and p[0][0] == "a":
            setr(p[0], None)
        elif mn == "exg":
            for q in p:
                setr(q, None)
        elif mn in NOWRITE:
            pass
        elif dst is not None and dst[0] in ("d", "a"):
            setr(dst, None)
        elif RE_DBCC.match(mn) and src[0] == "d":
            setr(src, None)
        return out

    # --- accesses ---------------------------------------------------------------------------------
    @staticmethod
    def mode(ins: Ins, i: int) -> str:
        """R, W, RW, A (address only), C (control flow) for operand i."""
        mn, n = ins.mn, len(ins.pops)
        if mn in ("lea", "pea"):
            return "A"
        if mn in ("jmp", "jsr"):
            return "C"
        if mn == "movem":
            return "W" if i == 1 and ins.pops[0][0] in ("list", "d", "a") else "R"
        if mn == "movep":
            return "W" if i == 1 else "R"
        if mn in ("move", "movea"):
            return "R" if i == 0 else "W"
        if mn in ("cmp", "cmpa", "cmpi", "cmpm", "tst", "btst", "chk"):
            return "R"
        if mn == "clr" or RE_SCC.match(mn):
            return "W"
        if n == 1:
            return "RW"
        return "R" if i == 0 else "RW"

    def events(self, ins: Ins, st: dict):
        """Yield (kind, ea, touched addresses, rw, via, indexed) for one instruction."""
        mn, sz, p = ins.mn, ins.sz, ins.pops
        nb = SIZE_BYTES.get(sz or "w", 2)
        for i, q in enumerate(p):
            md_ = self.mode(ins, i)
            if md_ == "C":
                continue
            t = q[0]
            ea = None
            via = None
            idx = False
            if t == "abs":
                ea = q[1]
            elif t == "pcd":
                ea = q[1]
            elif t in ("ind", "post", "pre", "disp", "idx"):
                k = ("a", q[1])
                if k not in st:
                    continue
                base, src = st[k]
                via = f"a{q[1]}=${base:x}@{src:x}"
                if t == "ind" or t == "post":
                    ea = base
                elif t == "pre":
                    ea = base - nb
                elif t == "disp":
                    ea = base + q[2]
                else:
                    ea = base + q[2]
                    idx = True
                ea &= M32
            elif t == "imm" and mn in ("move", "movea", "pea", "adda", "add", "sub", "suba", "lea"):
                v = q[1] & M32
                if sz == "w":
                    if p[-1][0] != "a":
                        continue
                    v = self.sext16(v)
                elif sz != "l":
                    continue
                if is_io(v) and region_of(v & 0xFFFFFF):
                    yield ("ptr", v, [v], "A", None, False)
                continue
            if ea is None:
                continue
            if md_ == "A":
                if is_io(ea) and region_of(ea & 0xFFFFFF):
                    yield ("ptr", ea, [ea], "A", via, idx)
                continue
            if mn == "movep":
                span, stride = nb, 2
            elif mn == "movem":
                other = p[1 - i] if len(p) == 2 else None
                regs = other[1] if other and other[0] == "list" else ({(other[0], other[1])} if other and other[0] in ("d", "a") else set())
                span, stride = len(regs) * nb, 1
                if t == "pre":
                    ea = (ea + nb) - span
            else:
                span, stride = nb, 1
            touched = [(ea + k * stride) & M32 for k in range(max(span, 1))]
            if is_io(ea):
                yield ("acc", ea, touched, md_, via, idx)
            elif md_ == "W" and 8 <= ea < 0x180 and not idx and mn in ("move", "clr", "movem"):
                yield ("vec", ea, touched, md_, via, idx)

    # --- reporting ----------------------------------------------------------------------------------
    def dataflow(self):
        code = self.code
        preds: dict[int, list[int]] = {a: [] for a in code}
        succs: dict[int, list[tuple[int, str]]] = {}
        for a, ins in code.items():
            kind, tg, falls, _ = self.flow(ins)
            s = []
            for t, _h in tg:
                if t in code:
                    s.append((t, "jump" if kind != "call" else "call"))
            if falls and a + ins.size in code:
                s.append((a + ins.size, "fall" if kind != "call" else "after"))
            succs[a] = s
            for t, _ in s:
                preds[t].append(a)
        state: dict[int, dict | None] = {a: None for a in code}
        work = []
        for a in code:
            if a in self.entries or a in self.calls or not preds[a]:
                state[a] = {}
                work.append(a)
        seen_work = set(work)
        while work:
            a = work.pop()
            seen_work.discard(a)
            ins = code[a]
            out = self.transfer(ins, state[a])
            for t, how in succs[a]:
                o = {} if how == "after" else out
                cur = state[t]
                if cur is None:
                    state[t] = dict(o)
                    ch = True
                else:
                    new = {k: v for k, v in cur.items() if k in o and o[k][0] == v[0]}
                    ch = len(new) != len(cur)
                    # keep the origin address of the lower-addressed load for display
                    if ch:
                        state[t] = new
                if ch and t not in seen_work:
                    work.append(t)
                    seen_work.add(t)
        return state

    def findings(self):
        state = self.dataflow()
        out = []
        for a in sorted(self.code):
            ins = self.code[a]
            st = state.get(a) or {}
            for kind, ea, touched, rw, via, idx in self.events(ins, st):
                if kind == "vec":
                    out.append(dict(a=a, conf=self.conf[a], kind="vec", rw=rw, level=W, ins=ins.text, ea=ea,
                                    regs=f"VECTOR ${ea & ~3:x}", group="VECTOR",
                                    note=vec_note(ea),
                                    via=via, machines="all"))
                    continue
                names, rows, pads = [], [], []
                weak = False
                for t in touched:
                    t24 = t & 0xFFFFFF
                    r = region_of(t24)
                    if r is None:
                        if self.conf[a] == "L":                  # a bare number in unreached code: too weak
                            weak = True
                            break
                        r = (t24, t24, "IO_OTHER", "unknown", W, "unmapped I/O address: bus error on most machines")
                    nm = reg_name(t24, r) if r[2] != "IO_OTHER" else f"${t24:06x}"
                    if nm is None:                               # unnamed byte: the register group at its offset
                        if names and pads[-1] and rows[-1][2] == r[2]:
                            continue                             # same unnamed block as the byte before
                        nm = f"{r[2]}+${t24 - r[0]:x}"
                        pad = True
                    else:
                        pad = False
                    if kind == "acc" and r[2] == "YM_SELECT" and ea & 1 and t == ea:
                        r = (r[0], r[1], "YM_ODD", "ST decode, Falcon bus error", C, "odd YM address: not a register on any machine; mirrors bus-error on a Falcon")
                        nm = f"YM_ODD(${t24:06x})"
                    if not names or names[-1] != nm:
                        names.append(nm)
                        rows.append(r)
                        pads.append(pad)
                if weak:
                    continue
                if len(names) > 4:
                    names = [names[0], "..", names[-1], f"({len(names)} regs)"]
                if kind == "acc" and idx:
                    names[0] += "[+index]"
                if not all(pads):                        # drop the unnamed pad bytes of word/long accesses
                    names = [n for n, p_ in zip(names, pads) if not p_]
                top = max(rows, key=lambda r: r[4])
                out.append(dict(a=a, conf=self.conf[a], kind=kind, rw="P" if kind == "ptr" else rw, level=top[4],
                                ins=ins.text, ea=ea, regs="+".join(names), group=top[2], machines=top[3],
                                note=(f"pointer to {names[0]} loaded: {top[5]}" if kind == "ptr" else top[5]), via=via))
        return out


# ----------------------------------------------------------------------------------------------------
def load_tos(path: str, base: int):
    d = open(path, "rb").read()
    if struct.unpack_from(">H", d, 0)[0] != 0x601A:
        raise SystemExit(f"{path}: not a GEMDOS program (no $601a header); pass --range for a RAM dump")
    tl, dl, bl, sl = struct.unpack_from(">IIII", d, 2)
    img = bytearray(d[28:28 + tl + dl])
    p = 28 + tl + dl + sl
    first = struct.unpack_from(">I", d, p)[0] if p + 4 <= len(d) else 0
    if first:
        off = first
        p += 4
        while True:
            if off + 4 <= len(img):
                struct.pack_into(">I", img, off, (struct.unpack_from(">I", img, off)[0] + base) & M32)
            b = d[p] if p < len(d) else 0
            p += 1
            if b == 0:
                break
            off += 254 if b == 1 else b
    mem = bytes(base) + bytes(img) + bytes(bl)
    return mem, base, base + tl


def parse_range(s: str):
    lo, _, hi = s.partition("-")
    return int(lo, 16), int(hi, 16)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="RAM dump (file offset = address) with --range, or a GEMDOS program (.TOS/.PRG)")
    ap.add_argument("--range", help="hex LO-HI of the code in a RAM dump, e.g. af40-21100")
    ap.add_argument("--base", default="10000", help="hex relocation base for a GEMDOS program (default 10000)")
    ap.add_argument("--seed", action="append", default=[], help="hex entry address to start from (repeatable)")
    ap.add_argument("--min", choices=list(LEVELS), default="info", help="hide findings below this level")
    ap.add_argument("--no-ptr", action="store_true", help="hide pointer loads (lea $ff8800,a0 ...)")
    ap.add_argument("--hide-low", action="store_true", help="hide confidence-L findings (code reached by no known path)")
    ap.add_argument("--no-sweep", action="store_true", help="do not look for unreached code in the gaps")
    a = ap.parse_args(argv)

    if a.range:
        mem = open(a.file, "rb").read()
        lo, hi = parse_range(a.range)
        hi = min(hi, len(mem))
    else:
        mem, lo, hi = load_tos(a.file, int(a.base, 16))
    sc = Scan(mem, lo, hi)
    seeds = [lo] + [int(s, 16) for s in a.seed]
    if a.range:                                       # the dump's own vector table
        for v in range(8, 0x400, 4):
            t = struct.unpack_from(">I", mem, v)[0]
            if sc.inrange(t):
                seeds.append(t)
    sc.discover(seeds, not a.no_sweep)
    fs = [f for f in sc.findings() if f["level"] >= LEVELS[a.min] and not (a.no_ptr and f["kind"] == "ptr")
          and not (a.hide_low and f["conf"] == "L")]

    nh = sum(1 for c in sc.conf.values() if c == "H")
    nl = len(sc.conf) - nh
    bytes_code = sum(i.size for i in sc.code.values())
    print(f"hwscan {os.path.basename(a.file)}  range ${lo:x}-${hi:x}  code: {nh} instrs reached (H) + {nl} unreached-run (L), "
          f"{bytes_code} of {hi - lo} bytes ({100 * bytes_code / max(hi - lo, 1):.0f}%)")
    print()
    print(f"{'addr':>7} c rw  lvl   {'instruction':<34} {'register(s)':<30} {'via':<14} risk")
    for f in sorted(fs, key=lambda f: f["a"]):
        print(f"{f['a']:06x}  {f['conf'] if f['conf'] == 'H' else '?'} {f['rw']:<3} {LEVEL_NAME[f['level']]:<5} "
              f"{f['ins']:<34} {f['regs']:<30} {(f['via'] or ''):<14} {f['note']}")
    print()
    cnt = Counter()
    first: dict[tuple, int] = {}
    for f in fs:
        k = (f["level"], f["group"], f["machines"], f["kind"] == "ptr")
        cnt[k] += 1
        first.setdefault(k, f["a"])
    print("summary (level, group, machines: findings, first address):")
    for k in sorted(cnt, key=lambda k: (-k[0], k[1], k[3])):
        print(f"  {LEVEL_NAME[k[0]]:<5} {k[1]:<18} {k[2]:<36} {cnt[k]:>4}{' (pointer loads)' if k[3] else '':<17} first ${first[k]:x}")
    real = [f for f in fs if f["kind"] != "ptr"]
    print(f"\ntotal {len(fs)} lines: {len(real)} accesses/vector writes "
          f"({sum(1 for f in real if f['conf'] == 'L')} low-confidence), {len(fs) - len(real)} pointer loads; "
          f"{sum(1 for f in fs if f['level'] == C)} crit")
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    sys.exit(main())
