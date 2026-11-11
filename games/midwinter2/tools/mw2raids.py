#!/usr/bin/env python3
"""Drive Midwinter 2 "Raids": pick an island on the Raids map and enter its 3D view.

Flow (all coordinates are screenshot pixels, see mw2harness.Hatari.goto):
  corridor -> RAIDS door -> level of play (NOVICE) -> "Select mission" island map
  -> hover island + SPACE (sets $eb9c = island id, shows the island text)
  -> question-mark icon -> boss screen -> thumbs up -> vehicle wireframe loading
  screen -> 3D view in the raid's starting vehicle ($6220 = vehicle type).

Usage:
  python3 tools/mw2raids.py cold ISLAND_X ISLAND_Y    # from a cold boot
  python3 tools/mw2raids.py map [--out work/snapshots/raids_map.sav]  # save a map-screen state
  python3 tools/mw2raids.py survey [--snapshot work/snapshots/raids_map.sav]

Library:
  from mw2raids import cold_to_raid_map, enter_raid, survey
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mw2harness import Hatari, GAME_DIR  # noqa: E402

ISLAND_ID = 0xEB9C        # word; $ffff before a selection, then the island id (Lobos = 2)
VEHICLE = 0x6220          # word; index into the 22 vehicle names
VIEW = 0x700A             # word; 2 in the 3D view
NAMES = ["Tank", "Jeep", "Truck", "Bus", "Train", "on foot", "Speedboat", "Crawler",
         "Minisub", "Submarine", "Ship", "Frogman", "Biplane", "Helicopter", "Zeppelin",
         "Balloon", "Rocket Pack", "Parachute", "Flying Boat", "Hovercraft", "Flying Sub",
         "Swimming"]
MAP_SNAPSHOT = GAME_DIR / "work" / "snapshots" / "raids_map.sav"
WARROOM_SNAPSHOT = GAME_DIR / "work" / "snapshots" / "warroom_campaign.sav"


def _enter_raids_from_hall(h: Hatari, level: tuple[int, int] = (175, 390)):
    """Corridor -> RAIDS door -> level of play -> island map."""
    for _ in range(4):
        h.goto(300, 230); h.click()                           # RAIDS door (a Hatari TT needs 10-60 s to load the screen: poll)
        t0 = time.time()
        while time.time() - t0 < 60:
            time.sleep(3 if time.time() - t0 > 9 else 10 - (time.time() - t0))
            if h.peekw(ISLAND_ID) == 0xFFFF and _screen_has_levels(h):
                break
        else:
            continue
        break
    else:
        raise RuntimeError("never reached the level-of-play screen")
    h.goto(*level); h.click(); time.sleep(12)                # NOVICE -> select-mission map
    h.center(); h.goto(100, 60); time.sleep(1)               # park the pointer on the border


def _screen_has_levels(h: Hatari) -> bool:
    """The level-of-play screen is the only one with a big black-suit portrait and
    four face buttons; test the 'SELECT LEVEL OF PLAY' caption row for white text."""
    from PIL import Image
    img = Image.open(h.shot()).convert("RGB")
    ox, oy = (96, 58) if img.width == 640 else (0, 0)          # TT shots have no border
    img = img.crop((290 - ox, 322 - oy, 540 - ox, 346 - oy))
    white = img.convert("L").point(lambda v: 255 if v > 200 else 0).histogram()[255]
    return white > 150


def cold_to_raid_map(h: Hatari, mode: str = "M"):
    """Cold boot (snapshot=None) -> the Raids island map. About 2 min of wall time."""
    time.sleep(25)
    ref = GAME_DIR / "work" / "ref" / "mode_select.png"
    for _ in range(40):
        h.cmd("hatari-event keypress 57"); time.sleep(5)
        if h.screen_matches(ref, (280, 350, 560, 420)):
            break
    else:
        raise RuntimeError("never reached the M/J/K screen")
    for _ in range(5):
        time.sleep(3)
        h.cmd(f"hatari-event keypress {dict(M=50, J=36, K=37)[mode]}"); time.sleep(5)
        if not h.screen_matches(ref, (280, 350, 560, 420)):
            break
    else:
        raise RuntimeError("M/J/K key not accepted")
    time.sleep(4)
    _enter_raids_from_hall(h)


def warroom_to_raid_map(h: Hatari):
    """From work/snapshots/warroom_campaign.sav (campaign menu): door icon -> corridor -> Raids map."""
    time.sleep(4)
    h.goto(230, 415); h.click(); time.sleep(8)
    _enter_raids_from_hall(h)


def _hud_up(h: Hatari) -> bool:
    """True once the 3D-view HUD frame is on screen (sky-blue / dark-blue panel pixels)."""
    from PIL import Image
    img = Image.open(h.shot()).convert("RGB")
    if img.width == 640:                                       # Hatari's TT draws one palette per frame: no HUD colours to test; use the view word
        return h.peekw(VIEW) == 2
    ox, oy = 0, 0
    return img.getpixel((100 - ox, 100 - oy)) == (0, 170, 238) and img.getpixel((730 - ox, 100 - oy)) == (0, 34, 136)


def enter_raid(h: Hatari, x: int, y: int, wait: float = 360, settle: float = 3, brief_shot: str | None = None) -> dict:
    """On the island map: hover (x, y), SPACE, '?' icon, thumbs up, wait for the 3D view.
    `settle` = seconds to wait after the HUD appears (use 0 for Parachute starts: the
    player lands and becomes Swimming/foot within seconds). Returns {'island': $eb9c, 'vehicle': $6220, 'view': $700a}. island == 0xffff means
    SPACE selected nothing."""
    boss = GAME_DIR / "work" / "ref" / "boss_thumbs.png"
    h.goto(x, y); h.key("space"); time.sleep(6)
    island = h.peekw(ISLAND_ID)
    if island == 0xFFFF:
        return {"island": island, "vehicle": None, "view": None}
    time.sleep(24)                                           # island text + picture load
    if brief_shot:
        h.shot(brief_shot)
    for _ in range(6):                                       # clicks are lost while a page loads
        h.goto(140, 415); h.click(); time.sleep(8)
        if h.screen_matches(boss, (590, 60, 740, 125)):
            break
    else:
        raise RuntimeError("never reached the thumbs-up screen")
    h.goto(625, 92); h.click()
    t0 = time.time()
    while time.time() - t0 < wait:                           # wait for the HUD frame in the screenshot
        time.sleep(1 if settle == 0 else 5)
        if h.peekw(VEHICLE) != 0xFFFF and _hud_up(h):
            break
    else:
        raise RuntimeError(f"3D view never appeared ($6220={h.peekw(VEHICLE):#x})")
    time.sleep(settle)
    return {"island": island, "vehicle": h.peekw(VEHICLE), "view": h.peekw(VIEW)}


def survey(points, snapshot=MAP_SNAPSHOT, shots=None, snaps=None, log=print):
    """For each (x, y) restore the map-screen snapshot and enter that island's raid."""
    out = []
    for x, y in points:
        h = Hatari(snapshot=str(snapshot), memsize_kb=2048)
        try:
            time.sleep(4)
            r = enter_raid(h, x, y, brief_shot=str(Path(shots) / f"brief_{x}_{y}.png") if shots else None)
            r["xy"] = (x, y)
            if shots and r["vehicle"] is not None:
                h.shot(str(Path(shots) / f"raid_{r['island']:02d}.png"))
            if snaps and r["vehicle"] is not None:
                h.savemem(str(Path(snaps) / f"island_{r['island']:02d}.sav"))
            log(r)
            out.append(r)
        finally:
            h.close()
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["cold", "map"])
    ap.add_argument("xy", nargs="*", type=int)
    ap.add_argument("--out", default=str(MAP_SNAPSHOT))
    a = ap.parse_args(argv)
    h = Hatari(snapshot=None, memsize_kb=1024, game_dir=GAME_DIR / "build" / "game")
    try:
        cold_to_raid_map(h)
        if a.cmd == "map":
            h.savemem(a.out)
        else:
            print(enter_raid(h, a.xy[0], a.xy[1]))
            print(h.shot())
    finally:
        h.close()


if __name__ == "__main__":
    main()
