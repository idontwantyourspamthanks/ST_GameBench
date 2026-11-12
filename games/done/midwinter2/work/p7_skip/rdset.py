#!/usr/bin/env python3
"""Parse a Hatari `trace cpu_disasm,cpu_regs` log of one render call and compute the memory
read-before-write byte set (inputs) and the write set.   usage: rdset.py trace.txt [out.json]"""
import re, sys, json, collections

HDR = re.compile(r'^([0-9a-f]{8}) ((?:[0-9a-f]{4} ?)+?)\s{2,}(\S+)\s*(.*)$')
SIZE = {'b': 1, 'w': 2, 'l': 4}

def split_ops(s):
    out, d, cur = [], 0, ''
    for ch in s:
        if ch == '(': d += 1
        elif ch == ')': d -= 1
        if ch == ',' and d == 0:
            out.append(cur.strip()); cur = ''
        else:
            cur += ch
    if cur.strip(): out.append(cur.strip())
    return out

ABS = re.compile(r'^\$([0-9a-f]{8})(?:\.[wl])?\s*(?:\[([0-9a-f]+)\])?$')
EAR = re.compile(r'==\s*\$([0-9a-f]+)')

def mem_ea(op):
    """Return EA of a memory operand or None (register/immediate/none)."""
    op = op.strip()
    if op.startswith('#'): return None
    m = EAR.search(op)
    if m:
        # exclude branch targets (handled by caller)
        return int(m.group(1), 16)
    m = ABS.match(op)
    if m: return int(m.group(1), 16)
    return None

RMW = {'add','sub','and','or','eor','addi','subi','andi','ori','eori','addq','subq','addx','subx','neg','negx','not',
       'asl','asr','lsl','lsr','rol','ror','roxl','roxr','bset','bclr','bchg','tas','nbcd','abcd','sbcd'}
READONLY = {'cmp','cmpi','cmpa','cmpm','tst','btst','mulu','muls','divu','divs','chk'}
NOMEM = {'lea','pea','jmp','jsr','bsr','bra','rts','rte','rtr','rtd','nop','dbf','dbra','link','unlk','swap','ext','exg','moveq','trap','illegal','stop','reset','dbcc'}

NEXTPC = True
def parse(path, in_range=None):
    lines = open(path, errors='replace').read().split('\n')
    recs = []
    for i, l in enumerate(lines):
        m = HDR.match(l)
        if not m: continue
        if i + 1 < len(lines) and lines[i+1].startswith('Next PC:'):
            nxt = int(lines[i+1].split(':')[1], 16)
            recs.append((int(m.group(1), 16), m.group(3), m.group(4), nxt, l))
        elif not NEXTPC:
            recs.append((int(m.group(1), 16), m.group(3), m.group(4), 0, l))
    return recs

def accesses(mn, ops_s):
    """-> list of (kind, ea, size) with kind in 'R','W' ; RMW produces R then W."""
    base = mn.split('.')[0].lower()
    suf = mn.split('.')[1] if '.' in mn else 'w'
    sz = SIZE.get(suf[0], 2) if suf else 2
    ops = split_ops(ops_s)
    out = []
    if base in NOMEM or base.startswith('b') and base not in ('btst','bset','bclr','bchg') or base.startswith('db') or base.startswith('s') and base not in ('sub','subi','subq','subx','sbcd','swap','suba','subaq') :
        # branches and scc: scc writes a byte
        if base.startswith('s') and base not in ('sub','subi','subq','subx','sbcd','swap','suba','subaq') and len(ops)==1:
            ea = mem_ea(ops[0])
            if ea is not None: out.append(('W', ea, 1))
        return out
    if base == 'movem':
        rl = [o for o in ops]
        # count regs in the register-list operand
        def nregs(s):
            n = 0
            for part in s.split('/'):
                part = part.strip()
                if '-' in part:
                    a, b = part.split('-'); n += abs(int(b[1]) - int(a[1])) + 1
                elif part: n += 1
            return n
        if len(ops) == 2:
            a, b = ops
            if EAR.search(b) and not EAR.search(a):  # reglist -> mem
                ea = mem_ea(b); n = nregs(a)
                pre = b.startswith('-(')
                if pre: out.append(('W', ea, n*sz))
                else: out.append(('W', ea, n*sz))
            elif EAR.search(a):                      # mem -> reglist
                ea = mem_ea(a); n = nregs(b)
                out.append(('R', ea, n*sz))
        return out
    if base == 'movep':
        for o in ops:
            ea = mem_ea(o)
            if ea is not None:
                out.append(('W' if ops.index(o) == 1 else 'R', ea, 2 if suf=='w' else 4))
        return out
    if base in ('move', 'movea'):
        if len(ops) == 2:
            s = mem_ea(ops[0]); d = mem_ea(ops[1])
            if s is not None: out.append(('R', s, sz))
            if d is not None: out.append(('W', d, sz))
        return out
    if base in ('clr', 'st'):
        d = mem_ea(ops[0]) if ops else None
        if d is not None: out.append(('W', d, sz))
        return out
    if base in READONLY or base in ('adda','suba','addaq','subaq'):
        for o in ops:
            ea = mem_ea(o)
            if ea is not None: out.append(('R', ea, sz if not (base in ('mulu','muls','divu','divs')) else 2))
        return out
    if base in RMW:
        if len(ops) == 1:
            ea = mem_ea(ops[0])
            if ea is not None: out += [('R', ea, sz), ('W', ea, sz)]
        elif len(ops) == 2:
            s = mem_ea(ops[0]); d = mem_ea(ops[1])
            if s is not None: out.append(('R', s, sz))
            if d is not None: out += [('R', d, sz), ('W', d, sz)]
        return out
    # unknown: report as R of every memory operand, flag
    for o in ops:
        ea = mem_ea(o)
        if ea is not None: out.append(('U', ea, sz))
    return out

def analyze(path, ignore_isr=True):
    recs = parse(path)
    firstR = {}   # byte -> pc of first read-before-write
    written = set()
    unk = collections.Counter()
    cntR = collections.Counter()
    n = 0; skipped = 0
    isr_stack = []
    ENTRY = {0x263de, 0x26298, 0x26882}   # $26a50 is a bare `rte` (timer C and the exit of $26882)
    for (pc, mn, ops, nxt, line) in recs:
        if pc in ENTRY and (not isr_stack or True):
            isr_stack.append(pc)
        if isr_stack:
            skipped += 1
            if mn.startswith('rte'): isr_stack.pop()
            continue
        n += 1
        for kind, ea, size in accesses(mn, ops):
            if kind == 'U': unk[mn.split('.')[0]] += 1; kind = 'R'
            if ea is None: continue
            for b in range(ea, ea + size):
                if kind == 'R':
                    if b not in written and b not in firstR: firstR[b] = pc
                else:
                    written.add(b)
    return n, skipped, firstR, written, unk

def intervals(bytes_):
    out = []; s = e = None
    for b in sorted(bytes_):
        if s is None: s = e = b
        elif b == e + 1: e = b
        else: out.append((s, e)); s = e = b
    if s is not None: out.append((s, e))
    return out

if __name__ == '__main__':
    n, sk, firstR, written, unk = analyze(sys.argv[1])
    print('instr', n, 'isr-skipped', sk, 'read-before-write bytes', len(firstR), 'written bytes', len(written), 'unknown-mn', dict(unk))
    iv = intervals(firstR.keys())
    if len(sys.argv) > 2:
        json.dump({'rbw': iv, 'first_pc': {hex(b): hex(p) for b, p in list(firstR.items())[:0]}}, open(sys.argv[2], 'w'))
    # merge gaps <= 8 for display
    merged = []
    for s, e in iv:
        if merged and s - merged[-1][1] <= 8: merged[-1][1] = e
        else: merged.append([s, e])
    for s, e in merged:
        print(f'{s:06x}-{e:06x} {e-s+1}')
