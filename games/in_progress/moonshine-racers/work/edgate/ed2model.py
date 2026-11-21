"""Python model of the milestone 2 editing rules of msedit.s (segment list + object list, the same arithmetic): used to predict what the editor must produce for an edit script,
and to encode it with tools/msrtrack.py's own encoder.  Every op returns None (done) or an error code string (refused: the model state is left as before, as the editor restores its history entry)."""
import copy, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import msrtrack as mt

MAXSEG, MAXOBJ = 2048, 999
HH = [8, 20, 40]


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
    def seg_split(self, k, pos):
        def f():
            if len(self.segs) >= MAXSEG: return "FULLSEG"
            s = self.segs[k]
            if not (pos > s[0] and pos - s[0] < s[1]): return "SPLIT"
            new = list(s); new[0] = pos; new[1] = s[1] - (pos - s[0]); s[1] = pos - s[0]
            self.segs.insert(k + 1, new)
        return self._do(f)
    def seg_merge(self, k):
        def f():
            if k >= len(self.segs) - 1: return "LAST"
            self.segs[k][1] += self.segs[k + 1][1]; del self.segs[k + 1]
            return "HILL" if self.hill_ovf() else None
        return self._do(f)

    # ---- objects
    def obj_add(self, pos):
        def f():
            if pos == 0: return "OBJ0"
            if len(self.objs) >= MAXOBJ: return "FULLOBJ"
            j = 0
            while j < len(self.objs) and self.objs[j][0] < pos: j += 1
            if j < len(self.objs) and self.objs[j][0] == pos: return "GAP"
            t = self.last_type or (1 if self.bar_t != 1 else 2)
            self.objs.insert(j, [pos, t, self.last_side])
        return self._do(f)
    def obj_del(self, j):
        def f():
            if self.objs[j][1] == self.bar_t: return "BARDEL"
            if len(self.objs) == 1: return None
            del self.objs[j]
        return self._do(f)
    def obj_move(self, j, delta):
        def f():
            lo = 1 if j == 0 else self.objs[j - 1][0] + 1
            hi = 32767 if j == len(self.objs) - 1 else self.objs[j + 1][0] - 1
            self.objs[j][0] = min(max(self.objs[j][0] + delta, lo), hi)
        return self._do(f)
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
    def bar_here(self, pos):
        def f():
            if pos == 0: return "OBJ0"
            if any(o[0] == pos and o[1] != self.bar_t for o in self.objs): return "GAP"
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
