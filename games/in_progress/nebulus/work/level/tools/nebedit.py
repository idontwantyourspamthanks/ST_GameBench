#!/usr/bin/env python3
"""nebedit: Nebulus level data reader/validator/patcher for NEBEXE.FIC (PP Gamex 'C3' packed file).

Prototype (design: work/notes/level.md section 7).  Everything here is from RAM/disassembly evidence in that note.

    python3 nebedit.py dump  NEBEXE.FIC [mission tower]     # names, times, palettes, ASCII map
    python3 nebedit.py set   NEBEXE.FIC OUT.FIC mission tower angle height hexval [...]   # value-only cell edits
    python3 nebedit.py time  NEBEXE.FIC OUT.FIC tower BCD    # initial time (e.g. 0x0999)
    python3 nebedit.py verify NEBEXE.FIC                     # unpack/pack round trip + structural checks

Unpacked-file offset  U = RAM - 0x33B1C + 28  (the image is a relocated GEMDOS program, text+data, loaded at RAM $33B1C).
No relocation entry points into any table edited here (checked in validate()).
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pplz  # noqa: E402

RAM0 = 0x33B1C          # RAM address of unpacked offset 28 (loaded text start)
HDR = 28
SETS = {1: 0x42BFA, 2: 0x44154}     # layout sets; $33910 = 1 -> first, else second ("Mission #1/#2")
SET_END = {1: 0x44153, 2: 0x456C1}  # end of the last tower stream of each set (set 1: 1 spare byte before set 2 at $44154)
TIME_TAB = 0x3AD9E                  # 8 words, BCD (0x0400 = 400)
NAME_PTRS = {1: 0x3D14E, 2: 0x3D16E}  # 8 longs each -> C strings
PALETTE = 0x35250                   # 8 x 16 words (STE 0x0RGB)
ROWS = 16                           # angular cells around a tower (8 px each, 128 px circumference)


def u(ram):
    return ram - RAM0 + HDR


class Nebulus:
    def __init__(self, path):
        self.path = Path(path)
        self.orig = self.path.read_bytes()
        data, self.lit = pplz.unpack(self.orig)
        self.img = bytearray(data)

    # --- raw access ---
    def b(self, ram, n=1):
        return bytes(self.img[u(ram):u(ram) + n])

    def w(self, ram):
        return struct.unpack(">H", self.b(ram, 2))[0]

    # --- tables ---
    def times(self):
        return [self.w(TIME_TAB + 2 * t) for t in range(8)]

    def set_time(self, tower, bcd):
        struct.pack_into(">H", self.img, u(TIME_TAB + 2 * tower), bcd)

    def name(self, mission, tower):
        p = struct.unpack(">L", self.b(NAME_PTRS[mission] + 4 * tower, 4))[0] + RAM0   # stored unrelocated
        s = self.b(p, 40)
        return s.split(b"\0")[0].decode("latin1")

    def palette(self, tower):
        return list(struct.unpack(">16H", self.b(PALETTE + 32 * tower, 32)))

    def tower_hdr(self, mission, tower):
        a3 = SETS[mission]
        t = a3 + 0x1000 + tower
        off = (self.b(t + 8)[0] << 8) | self.b(t)[0]
        return a3, off, self.b(t + 0x10)[0] + 1      # set base, stream offset, number of height rows

    def grid(self, mission, tower):
        """-> (grid[angle][height], stream_ram_addr[angle][height] or None, stream_end)"""
        a3, off, n = self.tower_hdr(mission, tower)
        mp, s = a3 + tower * 0x200, a3 + off
        g = [[0] * n for _ in range(ROWS)]
        addr = [[None] * n for _ in range(ROWS)]
        for c in range(n):
            for half in range(2):
                m = self.b(mp)[0]
                mp += 1
                for bit in range(8):
                    if m & (1 << bit):
                        g[half * 8 + bit][c] = self.b(s)[0]
                        addr[half * 8 + bit][c] = s
                        s += 1
        return g, addr, s

    def set_cell(self, mission, tower, ang, h, val):
        """Value-only edit: the cell must already be present in the stream (mask bit set)."""
        _, addr, _ = self.grid(mission, tower)
        a = addr[ang][h]
        if a is None:
            raise ValueError("cell (%d,%d) is empty; structural edits need encode_tower()" % (ang, h))
        self.img[u(a)] = val
        return a

    def relocs(self):
        """RAM addresses of the longs the loader relocates (+RAM0)."""
        tl = struct.unpack(">L", self.img[2:6])[0] + struct.unpack(">L", self.img[6:10])[0]
        rel = self.img[HDR + tl:]
        off = struct.unpack(">L", rel[:4])[0]
        i, offs = 4, [off]
        while rel[i] != 0:
            if rel[i] == 1:
                off += 254
            else:
                off += rel[i]
                offs.append(off)
            i += 1
        return [RAM0 + o for o in offs]

    # --- checks ---
    def validate(self):
        errs = []
        rl = self.relocs()
        for m in (1, 2):
            lo, hi = SETS[m], SET_END[m]
            bad = [hex(r) for r in rl if lo - 3 <= r < hi]
            if bad:
                errs.append("relocated longs inside layout set %d: %s" % (m, bad))
        for m in (1, 2):
            end_expected = SETS[m]
            prev_end = None
            for t in range(8):
                a3, off, n = self.tower_hdr(m, t)
                g, addr, send = self.grid(m, t)
                if not 1 <= n <= 256:
                    errs.append("m%d t%d bad row count %d" % (m, t, n))
                if prev_end is not None and a3 + off != prev_end:
                    errs.append("m%d t%d stream not contiguous (%x != %x)" % (m, t, a3 + off, prev_end))
                prev_end = send
                if sum(1 for r in g for v in r if v == 0xC3) != 3:
                    errs.append("m%d t%d: expected 3 exit-door cells (0xC3), got %d" % (m, t, sum(1 for r in g for v in r if v == 0xC3)))
            if prev_end != SET_END[m]:
                errs.append("m%d streams end %x, region ends %x" % (m, prev_end, SET_END[m]))
        return errs

    def ascii(self, mission, tower):
        g, _, _ = self.grid(mission, tower)
        n = len(g[0])
        out = []
        for c in range(n - 1, -1, -1):
            out.append("%2d " % c + " ".join(("%02x" % g[a][c]) if g[a][c] else ".." for a in range(ROWS)))
        return "\n".join(out)

    def save(self, out):
        Path(out).write_bytes(pplz.pack_file(self.orig, bytes(self.img)))


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd, path = argv[1], argv[2]
    nb = Nebulus(path)
    if cmd == "verify":
        again, _ = pplz.unpack(pplz.pack_file(nb.orig, bytes(nb.img)))
        print("round trip:", again == bytes(nb.img), "packed", len(pplz.pack_file(nb.orig, bytes(nb.img))), "orig", len(nb.orig))
        errs = nb.validate()
        print("validate:", errs or "OK")
    elif cmd == "dump":
        print("times", [hex(x) for x in nb.times()])
        for m in (1, 2):
            print("mission", m, [nb.name(m, t) for t in range(8)])
        if len(argv) >= 5:
            m, t = int(argv[3]), int(argv[4])
            print(nb.ascii(m, t))
    elif cmd == "set":
        out = argv[3]
        m, t = int(argv[4]), int(argv[5])
        rest = argv[6:]
        for i in range(0, len(rest), 3):
            a = nb.set_cell(m, t, int(rest[i]), int(rest[i + 1]), int(rest[i + 2], 16))
            print("cell -> RAM $%x unpacked $%x" % (a, u(a)))
        nb.save(out)
    elif cmd == "time":
        nb.set_time(int(argv[4]), int(argv[5], 16))
        nb.save(argv[3])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
