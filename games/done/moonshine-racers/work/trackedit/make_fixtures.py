#!/usr/bin/env python3
"""Regenerate the track fixtures from the stock level 0 (needs originals/MOONSHR/FILES/MS2).
    python3 work/trackedit/make_fixtures.py [OUTDIR]        default OUTDIR = work/trackedit/fixtures

edit1.json    level 0 with four hand edits, all inside the first 900 units so the standing start shows them:
              new bend (curve 100..400), a hill (height 0 -> ~60 -> 0 over units 100..300), a wider/narrower road (left 100..250 wide,
              right 300..500 narrow) and three moved objects.  Every ring stream still sums to 32768.
mixed.trk     version 2, four tracks that all finish flat out, own lengths and word 0 alternating (no leak of one race's length into the next):
              'LEN2 1000 L3' (word 1000), 'TEST ONE EDIT1 BEND' (c3.trk track 0: level 0, BAR at 700, word 0), 'LEN2 2000 L0' (word 2000), 'TEST TWO LEVEL 4 BASE' (c3.trk track 1: level 3, BAR at 800, word 0).
broken_*.json deliberately invalid tracks (each must be refused by `msrtrack.py validate`).
len2.trk      campaign file VERSION 2 for the loader gates (work/edgate/len2.py): stock-derived tracks with the BAR moved to the race length;
              the shortened ones have a STRAIGHT, flat road (curve and hill streams constant) so that a joystick-up-only run can finish them:
              0 'LEN2 2000 L0' scenery of level 0, own race length 2000;  1 'LEN2 1000 L3' level 3, own length 1000 (time bar on the 255-pass floor);
              2 'LEN2 6000 L4' level 4, own length 6000;  3 'LEN2 STOCK L9' level 9 untouched (word 0 = its own 20000);  4 'LEN2 6000 L0' level 0, own length 6000."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "tools"))
import msrtrack as M   # noqa: E402


def stock0():
    t, _ = M.decode_stock(M.read_ms2(None), 0)
    return t


def edit1():
    t = stock0()
    t["name"] = "EDIT1 BEND HILL"
    assert t["curve"][0] == [400, 0] and t["hill"][0] == [800, 0] and t["left"][0] == [430, 36] and t["right"][0] == [2010, 34]
    t["curve"][0:1] = [[100, 0], [80, 6], [60, 0], [80, -6], [80, 0]]                  # S-bend: heading rises to +480 then back to 0
    t["hill"][0:1] = [[100, 0], [50, 1600], [100, -1600], [50, 1600], [500, 0]]        # accel +/-1600: a smooth hill, ends flat again
    t["left"][0:1] = [[100, 36], [150, 70], [180, 36]]                                 # left half-width 36 -> 70 -> 36
    t["right"][0:1] = [[300, 34], [200, 15], [1510, 34]]                               # right half-width 34 -> 15 -> 34
    o = t["objects"]
    assert [x["at"] for x in o[2:8]] == [173, 231, 251, 261, 341, 411]
    o[2].update(at=190, lateral=-30)                                                   # moved
    o[5].update(at=275, lateral=0)                                                     # moved into the middle of the road
    o[7].update(at=450, lateral=-10)                                                   # moved
    return t


def shorten(lev, length, name, straight=True):
    """The stock track of `lev` with the finish BAR moved to unit `length` and the race length set to it (own race length);
    the stock objects behind the BAR up to 1500 units stay as run-out scenery, the rest of the stock road is untouched."""
    t, _ = M.decode_stock(M.read_ms2(None), lev)
    bar_types = {n + 1 for n, e in enumerate(t["types"]) if e[2] == M.BAR_SPRITE}
    bar = next(o for o in t["objects"] if o["type"] in bar_types)
    keep = [o for o in t["objects"] if o["type"] not in bar_types and (o["at"] < length - 4 or length + 20 < o["at"] <= length + 1500)]
    keep.append(dict(bar, at=length))
    keep.sort(key=lambda o: o["at"])
    t["objects"] = keep
    t["name"], t["race_length"] = name, length
    if straight:
        t["curve"] = [[M.RING, 0]]
        t["hill"] = [[M.RING, 0]]
    return t


def len2_campaign():
    ms2 = M.read_ms2(None)
    ts = [shorten(0, 2000, "LEN2 2000 L0"), shorten(3, 1000, "LEN2 1000 L3"), shorten(4, 6000, "LEN2 6000 L4")]
    ents = [(t["name"], t["base_level"], M.encode_track(t), M.race_word(t)) for t in ts]
    ents.append(("LEN2 STOCK L9", 9, M.decode_stock(ms2, 9)[1], 0))
    ts.append(shorten(0, 6000, "LEN2 6000 L0"))
    ents.append((ts[-1]["name"], 0, M.encode_track(ts[-1]), M.race_word(ts[-1])))
    for t in ts:
        errs = [i for i in M.validate_track(t) if i.level == "ERROR"]
        assert not errs, errs
    return M.build_campaign(ents)


def mixed_campaign():
    c3 = M.parse_campaign((HERE.parent / "camphd/camp/c3.trk").read_bytes())
    l2 = M.parse_campaign(len2_campaign())
    ents = [l2[1], c3[0], l2[0], c3[1]]
    return M.build_campaign([(e["name"], e["base"], e["block"], e["race"]) for e in ents])


def broken(kind):
    t = edit1() if kind != "stock" else stock0()
    if kind == "short":                       # curve stream ends 1000 units early: the game would run out of road before the finish + look-ahead
        while sum(c for c, _ in t["curve"]) > 20000:           # drop trailing segments: covers about 19.7k units < race length 19472 + 1024
            t["curve"].pop()
        t["name"] = "BROKEN SHORT CURVE"
    elif kind == "type":                      # object uses a type the base level does not have, lateral out of range
        t["objects"][10].update(type=200)
        t["objects"][11].update(lateral=300)
        t["name"] = "BROKEN BAD TYPE"
    elif kind == "gap":                       # objects out of order (gap 0 would end the list early) + width below the road minimum
        t["objects"][20]["at"] = t["objects"][19]["at"]
        t["right"][1][1] = 3
        t["name"] = "BROKEN GAP WIDTH"
    return t


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "fixtures"
    out.mkdir(parents=True, exist_ok=True)
    (out / "edit1.json").write_text(M.dumps_json(edit1()))
    for k in ("short", "type", "gap"):
        (out / f"broken_{k}.json").write_text(M.dumps_json(broken(k)))
    (out / "len2.trk").write_bytes(len2_campaign())
    (out / "mixed.trk").write_bytes(mixed_campaign())
    print("wrote", ", ".join(sorted(p.name for p in out.glob("*.json"))) + ", len2.trk, mixed.trk", "to", out)
