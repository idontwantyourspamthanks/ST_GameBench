#!/usr/bin/env python3
"""Regenerate the track fixtures from the stock level 0 (needs originals/MOONSHR/FILES/MS2).
    python3 work/trackedit/make_fixtures.py [OUTDIR]        default OUTDIR = work/trackedit/fixtures

edit1.json    level 0 with four hand edits, all inside the first 900 units so the standing start shows them:
              new bend (curve 100..400), a hill (height 0 -> ~60 -> 0 over units 100..300), a wider/narrower road (left 100..250 wide,
              right 300..500 narrow) and three moved objects.  Every ring stream still sums to 32768.
broken_*.json deliberately invalid tracks (each must be refused by `msrtrack.py validate`)."""
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
    print("wrote", ", ".join(sorted(p.name for p in out.glob("*.json"))), "to", out)
