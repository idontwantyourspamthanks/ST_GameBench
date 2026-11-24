"""Python model of the editing rules of msedit.s (segment list + object list, the same arithmetic; tile-grid editor of design section 15: split in half, objects added at the first free
unit of the selected segment, MOVE across segments, the BAR put into a segment, the tile words): used to predict what the editor must produce for an edit script,
and to encode it with tools/msrtrack.py's own encoder.  Every op returns None (done) or an error code string (refused: the model state is left as before, as the editor restores its history entry)."""
import copy, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import msrtrack as mt

MAXSEG, MAXOBJ = 2048, 999
HH = [8, 20, 40]
RLTAB = [19472, 19720, 19800, 19000, 19375, 18000, 18626, 20000, 19000, 20000, 20000, 22000, 18500, 22000, 23000]   # msedit.s rltab


def union(t):
    st = [list(map(list, t[k])) for k in ("curve", "left", "right", "hill")]
    ix = [0, 0, 0, 0]; rem = [s[0][0] for s in st]; pos = 0; out = []
    while pos < 32768 and len(out) < MAXSEG:
        n = min(min(rem), 32768 - pos)
        out.append([pos, n, st[0][ix[0]][1], st[3][ix[3]][1], st[1][ix[1]][1] & 0xff, st[2][ix[2]][1] & 0xff])
        pos += n; done = False
        for i in range(4):
            rem[i] -= n
            if rem[i] == 0:
                ix[i] += 1
                if ix[i] >= len(st[i]): done = True
                else: rem[i] = st[i][ix[i]][0]
        if done: break
    return out, pos


class Model:
    def __init__(self, t, straight=False):
        self.t = t; self.base = t["base_level"]
        self.types = t["types"]
        self.bar_t = next((n + 1 for n, e in enumerate(self.types) if e[2] == mt.BAR_SPRITE), 0)
        segs, total = union(t)
        self.total = total
        objs = [[o["at"], o["type"], o["lateral"]] for o in t["objects"]]
        if straight:
            w = segs[0]
            segs = [[0, 32768, 0, 0, w[4], w[5]]]; self.total = 32768
            objs = [o for o in objs if o[1] == self.bar_t][:1]
        self.segs, self.objs = segs, objs
        self.last_type = 0; self.last_side = 0
        self.hist = [self.snap()]; self.cur = 0

    def snap(self): return (copy.deepcopy(self.segs), copy.deepcopy(self.objs))
    def load(self, s): self.segs, self.objs = copy.deepcopy(s[0]), copy.deepcopy(s[1])
    def commit(self):
        self.hist = self.hist[:self.cur + 1]; self.hist.append(self.snap()); self.cur += 1
    def undo(self):
        if self.cur == 0: return "NOUNDO"
        self.cur -= 1; self.load(self.hist[self.cur])
    def redo(self):
        if self.cur + 1 >= len(self.hist): return "NOREDO"
        self.cur += 1; self.load(self.hist[self.cur])
    def _do(self, fn, *a):
        before = self.snap()
        err = fn(*a)
        if err: self.load(before); return err
        self.commit()

    # ---- the asm's helpers
    def obj_norm(self):
        o = self.objs
        if o and o[0][0] == 0: o[0][0] = 1
        for j in range(1, len(o)):
            if o[j][0] <= o[j - 1][0]: o[j][0] = (o[j - 1][0] + 1) & 0xffff
        return 1 if o and o[-1][0] > 32767 else 0

    def road_shift(self, P, delta, kfrom):
        last = self.segs[-1]
        if last[1] - delta < 16: return "ROOM"
        for j in range(kfrom, len(self.segs)): self.segs[j][0] = (self.segs[j][0] + delta) & 0xffff
        last[1] = last[1] - delta
        for o in self.objs:
            p = o[0]
            if p >= P: p = (p + delta) & 0xffff
            elif delta < 0 and p >= P + delta: p = P + delta
            o[0] = p
        if self.obj_norm(): return "OBJEND"

    def hill_ovf(self):
        d2 = d3 = 0
        for s in self.segs:
            for _ in range(s[1]):
                d3 += d2
                if not -2**31 <= d3 < 2**31: return True
                d2 += s[3]
                if not -2**31 <= d2 < 2**31: return True
        return False

    # ---- values
    def set_curve(self, k, v): return self._do(lambda: self.segs[k].__setitem__(2, v))
    def set_wl(self, k, v):
        def f():
            if not 10 <= v <= 85: return "RANGE"
            self.segs[k][4] = v
        return self._do(f)
    def set_wr(self, k, v):
        def f():
            if not 10 <= v <= 85: return "RANGE"
            self.segs[k][5] = v
        return self._do(f)
    def set_raw(self, k, v):
        def f():
            if not -6000 <= v <= 4000: return "RANGE"
            self.segs[k][3] = v
            if self.hill_ovf(): return "HILL"
        return self._do(f)
    def set_len(self, k, new):
        def f():
            if k >= len(self.segs) - 1: return "LAST"
            if new <= 0: return "RANGE"
            s = self.segs[k]; delta = new - s[1]
            if delta == 0: return None
            P = s[0] + s[1]; s[1] += delta
            return self.road_shift(P, delta, k + 1) or ("HILL" if self.hill_ovf() else None)
        return self._do(f)

    @staticmethod
    def accel(n, h):
        n2 = n * n; num = h << 16
        while n2 > 0xffff: n2 >>= 1; num >>= 1
        q = num // n2
        if q > 0xffff or q > 4000: q = 4000
        return max(q, 1)

    def hill_shape(self, k, s):
        def f():
            sg = self.segs[k]
            if s == 13: return None
            if s == 0: sg[3] = 0; return "HILL" if self.hill_ovf() else None
            fam, size = (s - 1) // 3, (s - 1) % 3
            h = HH[size]; L = sg[1]; pcs = []
            def add(n, a):
                if n == 0: return
                if pcs and pcs[-1][1] == a: pcs[-1][0] += n
                else: pcs.append([n, a])
            if fam < 2:
                n = L >> 1
                if n == 0: return "SHORT"
                a = self.accel(n, h); A = -a if fam == 1 else a
                add(n, A); add(L - 2 * n, 0); add(n, -A)
            else:
                n = L >> 2
                if n == 0: return "SHORT"
                a = self.accel(n, h); A = -a if fam == 3 else a
                add(n, A); add(n, -A); add(L - 4 * n, 0); add(n, -A); add(n, A)
            if len(self.segs) + len(pcs) - 1 > MAXSEG: return "FULLSEG"
            sg[1], sg[3] = pcs[0]
            for j in range(1, len(pcs)):
                prev = self.segs[k + j - 1]
                new = [(prev[0] + prev[1]) & 0xffff, pcs[j][0], prev[2], pcs[j][1], prev[4], prev[5]]
                self.segs.insert(k + j, new)
            return "HILL" if self.hill_ovf() else None
        return self._do(f)

    # ---- structure
    def seg_copy(self, k):
        def f():
            if k >= len(self.segs) - 1: return "LAST"
            if len(self.segs) >= MAXSEG: return "FULLSEG"
            s = self.segs[k]; P = s[0] + s[1]
            new = list(s); new[0] = P
            self.segs.insert(k + 1, new)
            return self.road_shift(P, s[1], k + 2) or ("HILL" if self.hill_ovf() else None)
        return self._do(f)
    def seg_del(self, k):
        def f():
            if k >= len(self.segs) - 1: return "LAST"
            s = self.segs[k]; P = s[0] + s[1]
            del self.segs[k]
            return self.road_shift(P, -s[1], k) or ("HILL" if self.hill_ovf() else None)
        return self._do(f)
    def seg_split(self, k):
        """S: cut in half (first part = length >> 1); the cursor stays on the first half"""
        def f():
            if len(self.segs) >= MAXSEG: return "FULLSEG"
            s = self.segs[k]; first = s[1] >> 1
            if first == 0: return "SPLIT"
            new = list(s); new[0] = s[0] + first; new[1] = s[1] - first; s[1] = first
            self.segs.insert(k + 1, new)
        return self._do(f)
    def seg_merge(self, k):
        def f():
            if k >= len(self.segs) - 1: return "LAST"
            self.segs[k][1] += self.segs[k + 1][1]; del self.segs[k + 1]
            return "HILL" if self.hill_ovf() else None
        return self._do(f)

    # ---- the grid's view of the model (calc_end, seg_last, seg_of, tiles_calc)
    def bar_at(self): return next((o[0] for o in self.objs if o[1] == self.bar_t), None) if self.bar_t else None
    def end(self):
        d = RLTAB[self.base] + 1024; b = self.bar_at()
        if b is not None and b + 512 > d: d = b + 512
        return min(d, self.total) & ~7
    def seg_last(self):
        e = self.end(); return max([k for k, s in enumerate(self.segs) if s[0] < e], default=0)
    def seg_of(self, unit):
        k = 0
        while k < len(self.segs) - 1 and unit >= self.segs[k + 1][0]: k += 1
        return k
    def seg_objs(self, k):
        s = self.segs[k]; return [j for j, o in enumerate(self.objs) if s[0] <= o[0] < s[0] + s[1]]
    def tiles(self):
        e = self.end(); c = 0; sl = 0; out = []
        s16 = lambda v: ((v + 0x8000) & 0xffff) - 0x8000
        s32 = lambda v: ((v + 0x80000000) & 0xffffffff) - 0x80000000
        for k, s in enumerate(self.segs):
            if s[0] >= e: out += [0x8000] * (len(self.segs) - k); break
            w = 0
            for j in self.seg_objs(k):
                w |= 0x40
                if self.bar_t and self.objs[j][1] == self.bar_t: w |= 0x80
            half = s[1] >> 1
            cm = s16(c + s[2] * half); base = 3 if cm >= 0 else 0; a = abs(cm)
            if a >= 300: w |= base + (1 if a < 1200 else 2 if a < 2400 else 3)
            sm = s32(sl + s[3] * half); base = 0 if sm >= 0 else 2; a = abs(sm)
            if a >= 1311: w |= (base + (1 if a < 6554 else 2)) << 3
            out.append(w)
            c = s16(c + s[2] * s[1]); sl = s32(sl + s[3] * s[1])
        return out

    # ---- objects
    def pick_unit(self, cand, k, bar_ok):
        s = self.segs[k]; occ = {o[0] for o in self.objs if not (bar_ok and o[1] == self.bar_t)}
        for u in list(range(cand, s[0] + s[1])) + list(range(s[0], cand)):
            if u != 0 and u not in occ: return u
        return 0
    def obj_add(self, k, after=None):
        """O (grid: after = None, from the middle of segment k) / I, O in the object list (after = the selected object's index: from the unit behind it)"""
        def f():
            if len(self.objs) >= MAXOBJ: return "FULLOBJ"
            s = self.segs[k]
            pos = self.pick_unit(self.objs[after][0] + 1 if after is not None else s[0] + (s[1] >> 1), k, False)
            if pos == 0: return "GAP"
            j = 0
            while j < len(self.objs) and self.objs[j][0] < pos: j += 1
            t = self.last_type or (1 if self.bar_t != 1 else 2)
            self.objs.insert(j, [pos, t, self.last_side])
        return self._do(f)
    def obj_del(self, j):
        def f():
            if len(self.objs) <= 1: return "LASTOBJ"
            if self.objs[j][1] == self.bar_t: return "BARDEL"
            del self.objs[j]
        return self._do(f)
    def obj_move(self, j, steps):
        """M, then the steps [('lr', +-1, units) | ('seg', +-1)], then Return: one history entry.  Returns the object's new index."""
        ob = self.objs[j]; e = self.end()
        def free(u): return not any(o is not ob and o[0] == u for o in self.objs)
        for st in steps:
            if st[0] == "lr":
                d = st[1]; u = min(max(ob[0] + d * st[2], 1), e - 1)
                while not free(u):
                    u += d
                    if not 1 <= u <= e - 1: u = None; break
            else:
                d = st[1]; k = self.seg_of(ob[0]); t = k + d; u = None
                if 0 <= t <= self.seg_last():
                    ts, tl = self.segs[t][0], self.segs[t][1]; last = min(ts + tl - 1, e - 1)
                    u = min(ts + ob[0] - self.segs[k][0], last) or 1
                    while not free(u):
                        u += d
                        if (d > 0 and u > last) or (d < 0 and (u == 0 or u < ts)): u = None; break
            if u is not None:
                ob[0] = u; self.objs.sort(key=lambda o: o[0]); e = self.end()
        self.commit()
        return next(i for i, o in enumerate(self.objs) if o is ob)
    def obj_type(self, j, t):
        def f():
            if self.objs[j][1] == self.bar_t: return "BART"
            self.objs[j][1] = t; self.last_type = t
        return self._do(f)
    def obj_side(self, j, v):
        def f():
            if not -128 <= v <= 127: return "LAT"
            self.objs[j][2] = v; self.last_side = v
        return self._do(f)
    def bar_here(self, k):
        """the BAR goes to the first free unit of segment k (BAR objects do not block) and keeps its side"""
        def f():
            if not self.bar_t: return "BART0"
            pos = self.pick_unit(self.segs[k][0], k, True)
            if pos == 0: return "GAP"
            lat = 0
            for j in range(len(self.objs) - 1, -1, -1):
                if self.objs[j][1] == self.bar_t: lat = self.objs[j][2]; del self.objs[j]
            j = 0
            while j < len(self.objs) and self.objs[j][0] < pos: j += 1
            self.objs.insert(j, [pos, self.bar_t, lat])
        return self._do(f)

    # ---- the block
    def track(self):
        t = dict(self.t)
        def stream(i):
            out = []
            for s in self.segs:
                if out and out[-1][1] == s[i]: out[-1][0] += s[1]
                else: out.append([s[1], s[i]])
            return out
        t["curve"], t["left"], t["right"], t["hill"] = stream(2), stream(4), stream(5), stream(3)
        t["objects"] = [{"at": o[0], "type": o[1], "lateral": o[2]} for o in self.objs]
        return t
    def block(self): return mt.encode_track(self.track())
