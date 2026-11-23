#!/usr/bin/env python3
"""Tile-grid editor: the screens of design section 15 on one boot (HD build, campaign c3.trk): a campaign track, a copy of an original track (grid, cursor moves, a row scroll,
the object list, an open pick list, the two HELP pages, the FIRE menu) and a plain straight (as created, and after two splits and an inserted copy).
   env7.sh python3 shots.py [--machine ste] [--mem 2048] [--tag T]
Every shot is also saved 3x enlarged without the border (<name>_x3.png).  Checks: the grid's shadow (what the editor believes each of the 128 slots shows) against the tile words,
and the screen RAM of every slot against a Python drawing of its tile word (the same rules as tile_draw)."""
import argparse
from ed2lib import *
from PIL import Image

ap = argparse.ArgumentParser(); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=2048); ap.add_argument("--tag"); ap.add_argument("--level", type=int, default=3)
ap.add_argument("--build", default=os.environ.get("ED_BUILD", "/tmp/msred7/hd"))
a = ap.parse_args()
tag = a.tag or f"shots_{ {'ste': 'ste', 'megaste': 'mste', 'st': 'st'}[a.machine] }{a.mem // 1024}m"
e = Ed(tag, a.machine, a.mem, a.build, CAMP / "c3.trk"); r = e.r
HILLCOL = [3, 8, 6, 4, 9]
GTAB = [[0x0180] * 7, [0x0c00, 0x0c00, 0x0600, 0x0600, 0x0300, 0x0300, 0x0180], [0x1800, 0x0c00, 0x0600, 0x0300, 0x0180, 0x00c0, 0x0060], [0, 0x3800, 0x0e00, 0x0380, 0x00e0, 0x0038, 0],
        [0x0060, 0x0060, 0x00c0, 0x00c0, 0x0180, 0x0180, 0x0300], [0x0030, 0x0060, 0x00c0, 0x0180, 0x0300, 0x0600, 0x0c00], [0, 0x0038, 0x00e0, 0x0380, 0x0e00, 0x3800, 0]]

def tile_px(w):
    """the 16 x 12 colour indices of a tile word (the rules of tile_draw)"""
    out = [[0] * 16 for _ in range(12)]
    if w & 0x8000: return out
    col = 7 if w & 0x80 else HILLCOL[(w >> 3) & 7]
    fr = 7 if w & 0x100 else 10 if w & 0x200 else 0
    for y in range(11):
        if w & 0x80: body = 0x3332 if y & 2 else 0xcccc
        else:
            body = 0xfffe
            if 2 <= y <= 8: body &= ~GTAB[w & 7][y - 2]
            elif y < 2 and w & 0x40: body &= 0xfff9
        ring = 0
        if fr:                                           # two pixel frame, a black ring, the tile's middle
            if 2 <= y <= 8: ring = 0xc006; body = body & 0x1ff0 if 3 <= y <= 7 else 0
            else:
                if w & 0x80: body = 0xfffe
                ring = body; body = 0
        for x in range(16):
            b = 0x8000 >> x
            out[y][x] = fr if ring & b else col if body & b else 0
    return out

def scr_px(scr, x, y):
    o = y * 160 + (x >> 4) * 8; b = 0x8000 >> (x & 15)
    return sum(((W(scr, o + 2 * p) & b) != 0) << p for p in range(4))

def grid_check(label):
    """shadow == tile words (+ the cursor's frame) for the visible window, and the screen RAM == the drawing of every slot"""
    e.idle(); t = e.tiles(); sh = e.shown(); first, seg, foc, nseg = e.vu("first"), e.vu("seg"), e.vu("focus"), e.vu("nseg")
    want = []
    for s in range(128):
        k = first + s
        w = t[k] if k < nseg else 0x8000
        if k == seg and not w & 0x8000: w |= 0x200 if foc else 0x100
        want.append(w)
    scr = e.screen(); bad = 0
    for s in range(128):
        px = tile_px(want[s]); x0, y0 = 32 + 16 * (s % 16), 8 + 12 * (s // 16)
        bad += sum(scr_px(scr, x0 + x, y0 + y) != px[y][x] for y in range(12) for x in range(16))
    nt = sum(1 for w in want if not w & 0x8000)
    check(f"[{label}] grid: first {first}, cursor {seg}, {nt} tiles; shadow == tile words; screen == the drawing of every slot", sh == want and bad == 0, f"shadow diffs {sum(x != y for x, y in zip(sh, want))}, wrong pixels {bad}")

def shot(name):
    p = r.shot(name)
    f = r.shotdir / f"{tag}_{name}.png"
    try:
        im = Image.open(f); im.crop((96, 58, 96 + 640, 58 + 400)).resize((960, 600), Image.NEAREST).save(r.shotdir / f"{tag}_{name}_x3.png")
    except Exception as ex: log("crop:", ex)
    log(f"shot {f.name}")

def state(label):
    log(f"[{label}] seg {e.vu('seg')}/{e.vu('nseg')} pos {e.vl('pos')} first {e.vu('first')} focus {e.vu('focus')} obj {e.vu('obj')} ocnt {e.vu('ocnt')} of {e.vu('of')} nobj {e.vu('nobj')} end {e.vl('end')} barat {e.vl('barat')} mod {e.vu('mod')} msg '{e.msgtext()}'")

try:
    e.boot_editor(True); shot("0_tracklist")
    # ---- a campaign track
    check("campaign track 1 opens", e.open_track("camp", 0)); state("camp"); grid_check("camp"); shot("camp_1_open")
    e.seg_goto(37); state("camp seg 37"); grid_check("camp seg 37"); shot("camp_2_seg38")
    e.send(0x30); e.idle(); state("camp B"); grid_check("camp BAR"); shot("camp_3_bar")
    e.send(0x0f); e.idle(); state("camp BAR, object list"); grid_check("camp BAR objects"); shot("camp_4_bar_objects")
    e.send(0x01); check("Esc: back to the track list (unchanged track)", e.wait(lambda: e.vu("state") == 0, 30)); time.sleep(1.5)
    # ---- a copy of an original track
    check(f"copy of original track {a.level + 1} opens", e.open_track("stock", a.level)); state("stock"); grid_check("stock"); shot("stock_1_open")
    e.key(0x4d, 5, 0.1); e.idle(); state("stock RIGHT x5"); grid_check("stock right 5"); shot("stock_2_right5")
    e.key(0x50, 7, 0.1); e.idle(); state("stock DOWN x7"); grid_check("stock down 7"); shot("stock_3_down7_scrolled")
    for k in range(e.vu("seg"), e.vu("seg") + 40):                 # the next segment that holds objects
        e.send(0x4d); e.idle()
        if e.vu("ocnt") >= 2: break
    e.send(0x0f); e.idle(); e.send(0x50); e.idle(); state("stock object list, 2nd object"); grid_check("stock objects"); shot("stock_4_objects")
    e.send(0x0f); e.idle()
    e.send(0x2e); e.wait(lambda: e.vu("lopen") == 1, 20); time.sleep(0.6); e.key(0x50, 3, 0.1); e.settle(); time.sleep(0.4); shot("stock_5_curve_list_preview")
    e.send(0x1c); e.wait(lambda: e.vu("lopen") == 0, 20); e.idle(); state("stock curve picked"); grid_check("stock after the curve pick"); shot("stock_6_curve_picked")
    e.send(0x23); e.wait(lambda: e.vu("lopen") == 1, 20); time.sleep(0.6); e.key(0x50, 2, 0.1); e.settle(); time.sleep(0.4); shot("stock_7_hill_list_preview")
    e.send(0x01); e.wait(lambda: e.vu("lopen") == 0, 20); e.idle(); grid_check("stock after the cancelled hill list")
    e.send(0x62); e.wait(lambda: e.vu("state") == 3, 20); time.sleep(0.8); shot("help_1_keys")
    e.send(0x39); e.wait(lambda: e.vu("page") == 2, 20); time.sleep(0.8); shot("help_2_legend")
    e.send(0x39); e.wait(lambda: e.vu("state") == 1, 20); e.idle(); grid_check("stock after HELP"); shot("stock_8_after_help")
    e.fire(); e.wait(lambda: e.vu("state") == 2, 20); time.sleep(0.6); shot("menu")
    e.send(0x01); e.wait(lambda: e.vu("state") == 1, 20); e.idle(); grid_check("stock after the menu")
    e.send(0x47); e.idle(); state("stock HOME"); grid_check("stock home")
    e.send(0x01); e.wait(lambda: e.vu("state") == 0, 60); time.sleep(1.5); log("left the copy:", e.msgtext())
    # ---- a plain straight (the copy above was kept: the campaign has four tracks now)
    check("plain straight opens", e.open_track("straight", a.level, ntr=r.w(V["count"]))); state("straight"); grid_check("straight"); shot("straight_1_new")
    e.send(0x1f); e.idle(); e.send(0x1f); e.idle(); e.send(0x26); e.wait(lambda: e.vu("lopen") == 1, 20); e.list_goto(5); e.send(0x1c); e.wait(lambda: e.vu("lopen") == 0, 20); e.idle()
    e.key(0x17, 6, 0.15); e.idle(); e.send(0x34); e.idle(); e.send(0x34); e.idle(); e.send(0x18); e.idle()
    state("straight edited"); grid_check("straight after S S L I x6 . . O"); shot("straight_2_edited")
    log(f"Bus/Address error lines in the Hatari log: {r.errlines()}")
except Exception:
    import traceback; log("EXCEPTION", traceback.format_exc()); FAILS.append("exception")
finally:
    e.close()
log(f"RESULT {tag}: {'ALL CHECKS PASS' if not FAILS else 'FAILED: ' + ', '.join(FAILS)}")
