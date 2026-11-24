#!/usr/bin/env python3
"""Tests for tools/msrtrack.py (stage 1).  Needs originals/MOONSHR/FILES/MS2.   python3 work/trackedit/test_msrtrack.py [-v]"""
import copy
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parents[1]
sys.path.insert(0, str(GAME / "tools"))
sys.path.insert(0, str(HERE))
import msrtrack as M            # noqa: E402
import make_fixtures as F       # noqa: E402

TOOL = [sys.executable, str(GAME / "tools/msrtrack.py")]
MS2 = M.read_ms2(None)


def cli(*args, ok=None):
    r = subprocess.run(TOOL + [str(a) for a in args], capture_output=True, text=True)
    if ok is not None:
        assert (r.returncode == 0) == ok, f"{args}: exit {r.returncode}\n{r.stdout}{r.stderr}"
    return r


def codes(issues):
    return {i.code for i in issues if i.level == "ERROR"}


class Stock(unittest.TestCase):
    def test_roundtrip_all_levels(self):
        for lev in range(M.NLEV):
            t, blk = M.decode_stock(MS2, lev)
            self.assertEqual(M.stock_block(MS2, lev)[:len(blk)], blk, lev)
            self.assertEqual(M.encode_track(json.loads(M.dumps_json(t))), blk, lev)
            self.assertEqual(M.parse_block(blk)[1], len(blk))
            self.assertEqual(codes(M.validate_track(t, budget=M.LEVELS[lev][M.LEV_NSECT] * 512, block=blk)), set(), lev)
            self.assertEqual(M.stock_race_length(MS2, lev), M.LEVELS[lev][M.LEV_LEN])

    def test_stock_streams_sum_32768(self):
        for lev in range(M.NLEV):
            t, _ = M.decode_stock(MS2, lev)
            for k in M.STREAMS:
                self.assertEqual(sum(c for c, _ in t[k]), 32768, (lev, k))


class Rules(unittest.TestCase):
    def setUp(self):
        self.t = F.edit1()

    def test_edit1_valid(self):
        self.assertEqual(codes(M.validate_track(self.t)), set())
        self.assertNotEqual(M.encode_track(self.t), M.decode_stock(MS2, 0)[1])

    def check(self, mutate, code):
        t = copy.deepcopy(self.t)
        mutate(t)
        self.assertIn(code, codes(M.validate_track(t)), code)

    def test_rejections(self):
        self.check(lambda t: t["curve"].__setitem__(slice(1, None), [[20000, 0]]), "E-SUM")
        self.check(lambda t: t["hill"].__setitem__(-1, [t["hill"][-1][0] - 20000, 0]), "E-STREAM")
        self.check(lambda t: t["objects"][3].update(type=0), "E-TYPE")
        self.check(lambda t: t["objects"][3].update(type=132), "E-TYPE")
        self.check(lambda t: t["objects"][3].update(lateral=128), "E-LAT")
        self.check(lambda t: t["objects"][4].update(at=t["objects"][3]["at"]), "E-GAP")
        self.check(lambda t: t["objects"][4].update(at=t["objects"][3]["at"] - 5), "E-GAP")
        self.check(lambda t: t["objects"][0].update(at=0), "E-OBJ")
        self.check(lambda t: t["left"].__setitem__(0, [100, 9]), "E-RANGE")
        self.check(lambda t: t["right"].__setitem__(0, [100, 86]), "E-RANGE")
        self.check(lambda t: t["curve"].__setitem__(0, [100, 11]), "E-RANGE")
        self.check(lambda t: t["curve"].__setitem__(0, [100, -10]), "E-RANGE")
        self.check(lambda t: t["hill"].__setitem__(0, [100, 4001]), "E-RANGE")
        self.check(lambda t: t.update(race_length=699), "E-RACELEN")
        self.check(lambda t: t.update(race_length=28001), "E-RACELEN")
        self.check(lambda t: t.update(race_length="x"), "E-FORM")
        self.check(lambda t: t["types"][0].__setitem__(2, 5), "E-TABLE")
        self.check(lambda t: t["types"].pop(), "E-TABLE")
        self.check(lambda t: t.update(base_level=15), "E-BASE")
        self.check(lambda t: t.update(name=""), "E-NAME")
        self.check(lambda t: t.update(name="X" * 25), "E-NAME")
        self.check(lambda t: t.update(bogus=1), "E-FORM")
        self.check(lambda t: t["hill"].__setitem__(0, [300, 4000]), "E-HILL")       # integrator overflow
        self.check(lambda t: t["curve"].__setitem__(0, [0, 0]), "E-STREAM")        # count 0 = terminator

    def test_bar_rule(self):
        """E-BAR: exactly one object of the base level's sprite-$21 type (the race ends when the car reaches it)."""
        bar_types = [n + 1 for n, e in enumerate(self.t["types"]) if e[2] == M.BAR_SPRITE]
        self.assertEqual(bar_types, [26])                         # level 0's finish type
        bars = [i for i, o in enumerate(self.t["objects"]) if o["type"] in bar_types]
        self.assertEqual(len(bars), 1)
        t = copy.deepcopy(self.t)                                  # no bar: the track can only end by time-out
        t["objects"][bars[0]]["type"] = 1
        self.assertIn("E-BAR", codes(M.validate_track(t)))
        t = copy.deepcopy(self.t)                                  # two bars
        t["objects"][bars[0] - 5]["type"] = 26
        self.assertIn("E-BAR", codes(M.validate_track(t)))
        t = copy.deepcopy(self.t)                                  # moving the bar anywhere is fine
        t["objects"][bars[0]]["lateral"] = 7
        self.assertNotIn("E-BAR", codes(M.validate_track(t)))
        for lev in range(M.NLEV):                                  # all 15 stock tracks have exactly one
            st, _ = M.decode_stock(MS2, lev)
            self.assertNotIn("E-BAR", codes(M.validate_track(st)), lev)

    def test_oversize(self):
        t = copy.deepcopy(self.t)
        last = t["objects"][-1]["at"]
        t["objects"] += [{"at": last + 1 + i, "type": 1, "lateral": 0} for i in range(400)]
        self.assertIn("E-SIZE", codes(M.validate_track(t)))

    def test_lenient_demotes_range(self):
        t = copy.deepcopy(self.t)
        t["curve"][0] = [100, 12]
        self.assertIn("E-RANGE", codes(M.validate_track(t)))
        self.assertNotIn("E-RANGE", codes(M.validate_track(t, lenient=True)))

    def test_budget(self):
        _, blk = M.decode_stock(MS2, 7)
        t, _ = M.decode_stock(MS2, 7)
        t["objects"] += [{"at": t["objects"][-1]["at"] + 1, "type": 1, "lateral": 0}]
        self.assertIn("E-SIZE", codes(M.validate_track(t, budget=len(blk) + 2)))

    def test_density_warning(self):
        t = copy.deepcopy(self.t)
        t["objects"][5:5 + 40] = [{"at": 300 + i, "type": 1, "lateral": 0} for i in range(40)]
        # keep order valid for the rest
        self.assertTrue(any(i.code == "W-DENS" for i in M.validate_track(t)) or "E-GAP" in codes(M.validate_track(t)))

    def test_block_truncated(self):
        _, blk = M.decode_stock(MS2, 3)
        for cut in (1, 3, 40, len(blk) - 14, len(blk) - 1):
            with self.assertRaises(M.TrackError):
                M.parse_block(blk[:len(blk) - cut] if cut < len(blk) else blk[:cut])
        # missing stream terminator: drop the zero word that ends S0 -> the curve list swallows the next stream and the block misparses
        with self.assertRaises(M.TrackError):
            M.parse_block(b"\x00\x05\x00\x01")


class Campaign(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="msrtrack_test_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def make(self):
        t = F.edit1()
        s5, _ = M.decode_stock(MS2, 5)
        return M.build_campaign([("EDIT1", 0, M.encode_track(t)), ("STOCK 05", 5, M.decode_stock(MS2, 5)[1])])

    def test_roundtrip_and_layout(self):
        f = self.make()
        ents = M.parse_campaign(f)
        self.assertEqual([e["name"] for e in ents], ["EDIT1", "STOCK 05"])
        self.assertEqual(f[:4], b"MSTK")
        self.assertEqual(struct.unpack_from(">HHL", f, 4)[:2], (1, 2))          # no own length: version 1 still
        self.assertEqual([e["race"] for e in ents], [0, 0])
        self.assertEqual(struct.unpack_from(">L", f, 8)[0], len(f))
        self.assertEqual(ents[0]["offset"], 16 + 40 * 2)
        self.assertEqual(ents[1]["offset"], ents[0]["offset"] + len(ents[0]["block"]))

    def test_corruptions(self):
        f = bytearray(self.make())
        bad = {
            "magic": lambda b: b.__setitem__(0, 0x58),
            "version": lambda b: b.__setitem__(5, 3),
            "count0": lambda b: b.__setitem__(7, 0),
            "count16": lambda b: b.__setitem__(7, 16),
            "table crc": lambda b: b.__setitem__(16 + 3, b[16 + 3] ^ 1),
            "block crc": lambda b: b.__setitem__(len(b) - 5, b[-5] ^ 0x40),
            "truncated": lambda b: b.__delitem__(slice(len(b) - 7, None)),
            "padded": lambda b: b.extend(b"\0\0"),
        }
        for k, fn in bad.items():
            g = bytearray(f)
            fn(g)
            with self.assertRaises(M.TrackError, msg=k):
                M.parse_campaign(bytes(g))

    def test_too_many_and_too_big(self):
        blk = M.decode_stock(MS2, 0)[1]
        with self.assertRaises(M.TrackError):
            M.build_campaign([("A", 0, blk)] * 16)
        with self.assertRaises(M.TrackError):
            M.build_campaign([("A", 0, blk + bytes(M.BLOCK_MAX))])
        M.build_campaign([("A", 0, blk)] * 15)

    def test_disk(self):
        f = self.make()
        img = M.build_disk(f)
        self.assertEqual(len(img), 737280)
        self.assertEqual(M.disk_read_file(img), f)
        self.assertEqual(M.disk_read_file(M.from_msa(M.to_msa(img))), f)
        self.assertEqual(M.build_disk(f), img)                     # deterministic
        self.assertNotEqual(sum(struct.unpack(">256H", img[:512])) & 0xFFFF, 0x1234)
        if shutil.which("mdir"):
            p = self.tmp / "c.st"
            p.write_bytes(img)
            r = subprocess.run(["mcopy", "-i", str(p), "::MSTRACKS.TRK", str(self.tmp / "back.trk")], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual((self.tmp / "back.trk").read_bytes(), f)
            r = subprocess.run(["mdir", "-i", str(p), "::"], capture_output=True, text=True)
            self.assertIn("MSTRACKS", r.stdout)

    def test_big_disk(self):
        f = M.build_campaign([(f"S{i}", i, M.decode_stock(MS2, i)[1]) for i in range(15)])
        self.assertEqual(M.disk_read_file(M.build_disk(f)), f)

    def test_patch_ms2(self):
        ents = M.parse_campaign(self.make())
        new, log = M.patch_ms2(MS2, ents[:1])
        s, n = M.LEVELS[0][0], M.LEVELS[0][1]
        self.assertEqual(len(new), len(MS2))
        self.assertEqual(new[:s * 512], MS2[:s * 512])
        self.assertEqual(new[(s + n) * 512:], MS2[(s + n) * 512:])
        self.assertEqual(new[s * 512:s * 512 + len(ents[0]["block"])], ents[0]["block"])
        stock = [dict(name="X", base=i, block=M.decode_stock(MS2, i)[1]) for i in range(M.NLEV)]
        self.assertEqual(M.patch_ms2(MS2, stock)[0], MS2)
        with self.assertRaises(M.TrackError):                      # one slot per level
            M.patch_ms2(MS2, [stock[3], stock[3]])
        big = dict(stock[7])
        big["block"] = big["block"] + bytes(20)
        with self.assertRaises(M.TrackError):                      # over the sector budget of slot 7 (4086 + 20 > 4096)
            M.patch_ms2(MS2, [big])


class RaceLength(unittest.TestCase):
    """Format version 2: the entry word +26 = the track's own race length (work/notes/editor_design.md 17.9, 17.10)."""
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="msrtrack_len_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.t = F.shorten(0, 2000, "SHORT TWO THOUSAND")

    def codes(self, t, w=False):
        return {i.code for i in M.validate_track(t) if w or i.level == "ERROR"}

    def test_stock_campaign_still_v1_bit_identical(self):
        ents = [(f"STOCK {lev:02d}", lev, M.decode_stock(MS2, lev)[1]) for lev in range(M.NLEV)]
        f = M.build_campaign(ents)
        self.assertEqual((len(f), f[4:6]), (64676, b"\0\1"))
        self.assertEqual(f, M.build_campaign([(n, b, k, 0) for n, b, k in ents]))
        back = M.parse_campaign(f)
        self.assertTrue(all(e["race"] == 0 and e["version"] == 1 for e in back))
        self.assertEqual(M.build_campaign([(e["name"], e["base"], e["block"], e["race"]) for e in back]), f)
        for lev in range(M.NLEV):                                       # the 15 stock tracks: word 0, encode == stock block
            t, blk = M.decode_stock(MS2, lev)
            self.assertEqual((M.race_word(t), M.encode_track(t)), (0, blk))

    def test_race_word_rule(self):
        t, _ = M.decode_stock(MS2, 0)
        self.assertEqual(M.race_word(t), 0)                             # equal to the base level's: the base level's
        t.pop("race_length")
        self.assertEqual(M.race_word(t), 0)                             # absent: the base level's
        self.assertEqual(M.race_word({**t, "race_length": 2000}), 2000)

    def test_v2_roundtrip(self):
        ms = [self.t, F.shorten(4, 6000, "SIX"), M.decode_stock(MS2, 9)[0]]
        ents = [(t["name"], t["base_level"], M.encode_track(t), M.race_word(t)) for t in ms]
        f = M.build_campaign(ents)
        self.assertEqual(f[4:6], b"\0\2")
        back = M.parse_campaign(f)
        self.assertEqual([e["race"] for e in back], [2000, 6000, 0])
        self.assertEqual(struct.unpack_from(">H", f, 16 + 26)[0], 2000)
        self.assertEqual(struct.unpack_from(">H", f, 16 + 40 + 26)[0], 6000)
        self.assertEqual(struct.unpack_from(">H", f, 16 + 80 + 26)[0], 0)
        self.assertEqual(M.build_campaign([(e["name"], e["base"], e["block"], e["race"]) for e in back]), f)
        for e, t in zip(back, ms):                                      # entry_track: the track dict carries the length (the base level's for word 0)
            t2, iss = M.entry_track(e)
            self.assertEqual((t2["race_length"], iss), (t["race_length"], []))
            self.assertEqual(M.race_word(t2), M.race_word(t))
            self.assertEqual(codes(M.validate_track(t2, block=e["block"])), set())
        self.assertEqual(M.disk_read_file(M.build_disk(f)), f)
        self.assertTrue(M.validate_campaign(f, "v2"))

    def test_v2_with_all_words_zero_is_readable(self):
        blk = M.decode_stock(MS2, 0)[1]
        f = bytearray(M.build_campaign([("A", 0, blk)]))
        f[5] = 2
        f[12:16] = struct.pack(">L", zlib.crc32(bytes(f[:12]) + bytes(f[16:56])))
        self.assertEqual(M.parse_campaign(bytes(f))[0]["race"], 0)

    def test_word_ranges(self):
        blk = M.decode_stock(MS2, 0)[1]
        for w in (1, 699, 28001, 32768, 65535):
            with self.assertRaises(M.TrackError, msg=w):
                M.build_campaign([("A", 0, blk, w)])
        for w in (700, 28000):
            M.parse_campaign(M.build_campaign([("A", 0, blk, w)]))
        for w, ver in ((300, 2), (29000, 2), (2000, 1)):                # a hand-patched file: the reader refuses what the game's check refuses
            f = bytearray(M.build_campaign([("A", 0, blk, 2000)]))
            f[5] = ver
            f[16 + 26:16 + 28] = struct.pack(">H", w)
            f[12:16] = struct.pack(">L", zlib.crc32(bytes(f[:12]) + bytes(f[16:56])))
            with self.assertRaises(M.TrackError, msg=(w, ver)):
                M.parse_campaign(bytes(f))

    def test_v11_refuses_v2_by_its_version_check(self):
        """cp_title `validate` of the released v1.1 game: `cmpi.w #1,4(a2) / bne .bad`: any file with an own length is version 2."""
        blk = M.decode_stock(MS2, 0)[1]
        v1 = M.build_campaign([("A", 0, blk), ("B", 0, blk, 0)])
        v2 = M.build_campaign([("A", 0, blk), ("B", 0, blk, 2000)])
        self.assertEqual(struct.unpack_from(">H", v1, 4)[0], 1)
        self.assertEqual(struct.unpack_from(">H", v2, 4)[0], 2)

    def test_validation(self):
        t = self.t
        self.assertEqual(self.codes(t, True), set())                    # 2000: BAR at 2000, streams 32768, no warnings
        self.assertIn("E-RACELEN", self.codes({**t, "race_length": 650}))
        self.assertIn("E-RACELEN", self.codes({**t, "race_length": 28100}))
        self.assertNotIn("E-RACELEN", self.codes({**t, "race_length": 28000}))
        self.assertNotIn("E-RACELEN", self.codes({**t, "race_length": 700}))
        self.assertIn("W-FINISH", self.codes({**t, "race_length": 3200}, True))     # BAR 1200 before the end of the race
        self.assertNotIn("W-FINISH", self.codes({**t, "race_length": 3100}, True))  # exactly 1100: allowed
        self.assertIn("W-FINISH", self.codes({**t, "race_length": 899}, True))
        s, _ = M.decode_stock(MS2, 0)
        self.assertNotIn("W-FINISH", self.codes(s, True))

    def test_esum_uses_length_and_bar(self):
        t = copy.deepcopy(self.t)
        t["race_length"] = 28000                                         # needs 29024 per ring stream: 32768 is fine
        self.assertNotIn("E-SUM", self.codes(t))
        for k in M.STREAMS:                                              # cut a stream to 3000 units: short of 2000 + 1024 ...
            u = copy.deepcopy(self.t)
            tot, out = 0, []
            for c, v in u[k]:
                take = min(c, 3023 - tot)
                if take > 0:
                    out.append([take, v])
                tot += c
            u[k] = out
            self.assertIn("E-SUM", self.codes(u), k)
            out[-1][0] += 1                                              # ... and exactly 2000 + 1024 passes
            self.assertNotIn("E-SUM", self.codes(u), k)
        u = copy.deepcopy(self.t)                                        # the BAR beyond the race length counts: BAR 2000, race 700 -> needs 3024
        u["race_length"] = 700
        for k in M.STREAMS:
            tot, out = 0, []
            for c, v in u[k]:
                take = min(c, 3023 - tot)
                if take > 0:
                    out.append([take, v])
                tot += c
            u[k] = out
        self.assertIn("E-SUM", self.codes(u))

    def test_json_roundtrip_and_cli(self):
        T = self.tmp
        (T / "s.json").write_text(M.dumps_json(self.t))
        r = cli("validate", T / "s.json", ok=True)
        cli("campaign", "new", T / "c.trk", T / "s.json", ok=True)
        f = (T / "c.trk").read_bytes()
        self.assertEqual((f[4:6], M.parse_campaign(f)[0]["race"]), (b"\0\2", 2000))
        r = cli("campaign", "list", T / "c.trk", ok=True)
        self.assertIn("v2", r.stdout)
        self.assertIn("2000*", r.stdout)
        cli("campaign", "extract", T / "c.trk", 0, "-o", T / "x.json", ok=True)
        self.assertEqual(json.loads((T / "x.json").read_text())["race_length"], 2000)
        cli("campaign", "add", T / "c.trk", T / "x.json", ok=True)              # re-adding the extracted JSON keeps the length
        self.assertEqual([e["race"] for e in M.parse_campaign((T / "c.trk").read_bytes())], [2000, 2000])
        cli("campaign", "remove", T / "c.trk", 0, ok=True)
        for lev in (1, 2, 3, 4):
            (T / f"b{lev}.json").write_text(M.dumps_json(M.decode_stock(MS2, lev)[0]))
        (T / "b.json").write_text((T / "b3.json").read_text())
        cli("campaign", "new", T / "s5.trk", *(T / f"b{lev}.json" for lev in (1, 2, 3, 4)), ok=True)
        cli("campaign", "add", T / "s5.trk", T / "s.json", "--at", 3, ok=True)
        self.assertEqual([e["race"] for e in M.parse_campaign((T / "s5.trk").read_bytes())], [0, 0, 0, 2000, 0])
        # a track with a base-level length writes version 1 again
        cli("campaign", "new", T / "b.trk", T / "b.json", ok=True)
        self.assertEqual((T / "b.trk").read_bytes()[4:6], b"\0\1")
        # patch-ms2 has no place for an own length
        r = cli("patch-ms2", T / "s5.trk", "-o", T / "m.new", ok=False)
        self.assertIn("own race length", r.stdout)
        self.assertFalse((T / "m.new").exists())
        cli("patch-ms2", T / "s5.trk", "-o", T / "m.new", "--force", ok=True)
        cli("render", T / "s.json", "-o", T / "r.png", ok=True)
        cli("render", T / "s5.trk", "--entry", 3, "-o", T / "r3.png", ok=True)
        cli("disk", T / "s5.trk", "-o", T / "s5.st", ok=True)
        cli("validate", T / "s5.st", ok=True)

    def test_mixed_campaign_fixture(self):
        f = (HERE / "fixtures/mixed.trk").read_bytes()
        self.assertEqual(f, F.mixed_campaign())
        ents = M.parse_campaign(f)
        self.assertEqual(f[4:6], b"\0\2")
        self.assertEqual([(e["base"], e["race"]) for e in ents], [(3, 1000), (0, 0), (0, 2000), (3, 0)])
        self.assertTrue(M.validate_campaign(f, "mixed"))
        # drop the own lengths again: byte for byte a version 1 file of the same blocks
        v1 = M.build_campaign([(e["name"], e["base"], e["block"]) for e in ents])
        self.assertEqual(v1[4:6], b"\0\1")
        self.assertEqual([e["block"] for e in M.parse_campaign(v1)], [e["block"] for e in ents])

    def test_fixture(self):
        fx = HERE / "fixtures/len2.trk"
        self.assertEqual(fx.read_bytes(), F.len2_campaign())
        ents = M.parse_campaign(fx.read_bytes())
        self.assertEqual([(e["base"], e["race"]) for e in ents], [(0, 2000), (3, 1000), (4, 6000), (9, 0), (0, 6000)])
        self.assertTrue(M.validate_campaign(fx.read_bytes(), "len2"))


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="msrtrack_cli_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_flow(self):
        T = self.tmp
        fx = HERE / "fixtures"
        cli("decode", "--all", "-o", T / "all", ok=True)
        self.assertEqual(len(list((T / "all").glob("*.json"))), 15)
        cli("validate", *sorted((T / "all").glob("*.json")), ok=True)
        cli("encode", fx / "edit1.json", "-o", T / "e.bin", ok=True)
        cli("validate", T / "e.bin", "--base", 0, ok=True)
        cli("campaign", "new", T / "c.trk", fx / "edit1.json", ok=True)
        r = cli("campaign", "list", T / "c.trk", ok=True)
        self.assertIn("EDIT1 BEND HILL", r.stdout)
        cli("campaign", "add", T / "c.trk", T / "all/level05.json", "--at", 0, ok=True)
        cli("campaign", "extract", T / "c.trk", 0, "-o", T / "x.json", ok=True)
        self.assertEqual(json.loads((T / "x.json").read_text())["base_level"], 5)
        cli("campaign", "extract", T / "c.trk", 1, "--bin", "-o", T / "x.bin", ok=True)
        self.assertEqual((T / "x.bin").read_bytes(), (T / "e.bin").read_bytes())
        cli("campaign", "remove", T / "c.trk", 0, ok=True)
        cli("disk", T / "c.trk", "-o", T / "c.st", ok=True)
        cli("disk", T / "c.trk", "-o", T / "c.msa", ok=True)
        cli("validate", T / "c.st", T / "c.msa", ok=True)
        cli("patch-ms2", T / "c.trk", "-o", T / "MS2.new", ok=True)
        self.assertEqual(len((T / "MS2.new").read_bytes()), len(MS2))
        cli("render", fx / "edit1.json", "-o", T / "r.png", ok=True)
        cli("render", 4, "-o", T / "r4.png", ok=True)
        self.assertTrue((T / "r.png").stat().st_size > 10000)

    def test_broken_refused(self):
        fx = HERE / "fixtures"
        for name, code in (("broken_short", "E-SUM"), ("broken_type", "E-TYPE"), ("broken_gap", "E-GAP")):
            r = cli("validate", fx / f"{name}.json", ok=False)
            self.assertIn(code, r.stdout, name)
            r = cli("encode", fx / f"{name}.json", "-o", self.tmp / "x.bin", ok=False)
            self.assertFalse((self.tmp / "x.bin").exists())
            r = cli("campaign", "new", self.tmp / "x.trk", fx / f"{name}.json", ok=False)
            self.assertFalse((self.tmp / "x.trk").exists())
        # raw block without its terminators
        blk = M.decode_stock(MS2, 2)[1]
        (self.tmp / "cut.bin").write_bytes(blk[:-14])
        r = cli("validate", self.tmp / "cut.bin", "--base", 2, ok=False)
        self.assertIn("E-TERM", r.stdout)
        # campaign with a flipped bit
        f = bytearray(M.build_campaign([("A", 2, blk)]))
        f[-10] ^= 1
        (self.tmp / "bad.trk").write_bytes(bytes(f))
        r = cli("validate", self.tmp / "bad.trk", ok=False)
        self.assertIn("CRC", r.stdout)

    def test_selftest(self):
        r = cli("selftest", ok=True)
        self.assertIn("SELFTEST PASS", r.stdout)


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]] + [a for a in sys.argv[1:]], verbosity=1)
