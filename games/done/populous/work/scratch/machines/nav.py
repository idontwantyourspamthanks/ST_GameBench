"""Navigation helpers for the cold-boot cells (test scaffolding)."""
import sys, time
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
from mm import *
REF = Path(__file__).resolve().parent / "ref"
HOME_ST, HOME_TT = (96, 58), (107, 67)

def crop_match(png, ref, box, tol=14):
    im = Image.open(png).convert("RGB").crop(box)
    d = ImageChops.difference(im, Image.open(ref).convert("RGB"))
    return sum(ImageStat.Stat(d).mean) / 3 < tol

def menu_seen(h, wide):
    """True if the TUTORIAL/CONQUEST/CUSTOM buttons are on screen. wide: TT/Falcon-sized shot (picture at 0,0)."""
    h.shot("/tmp/_nav_poll_%d.png" % id(h))
    p = "/tmp/_nav_poll_%d.png" % id(h)
    return crop_match(p, REF / "tt_menu_buttons.png", (460, 310, 640, 395))

def wait_menu(h, timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(1)
        try:
            if menu_seen(h, True):
                return time.time() - t0
        except Exception as e:
            return None
    return None
