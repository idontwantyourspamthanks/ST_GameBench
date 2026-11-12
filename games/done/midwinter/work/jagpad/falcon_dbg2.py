import sys, time
from jlib import *
import mw1
h = MW1(snapshot=None, game_dir=str(GAME/'build'/'jag'), machine='falcon', memsize_kb=4096, extra=PAD)
S = Sampler(h, [(0xb6bf0, 10), (0xb2ff8, 4), (0x2c178, 2), (0x12d5e, 4), (0x1efde, 2)])
def show(t):
    r = S(); print(t, 'vbl', r['vbl'], 'PAD', r[0xb6bf0].hex(), 'MWPO', r[0xb2ff8], '2c178', r[0x2c178].hex(), 'step', r[0x12d5e].hex(), 'menu', r[0x1efde].hex(), flush=True)
try:
    print('options', h.boot_to_options(timeout=300), flush=True)
    h.click_at(mw1.MODE_XY['J']); print(h.control_mode())
    h.click_at(mw1.MORTARS_XY); h.click_at(mw1.BOMBERS_XY); h.click_at(mw1.TRAINING_XY)
    h.click_at(mw1.PLAY_XY, 12); show('after PLAY'); h.shot('/tmp/fal_play.png')
    h.click_at(mw1.STARK_XY, 6); show('after Stark'); h.shot('/tmp/fal_stark.png')
    h.click_at(mw1.DECISIONS_XY, 6); show('after Decisions'); h.shot('/tmp/fal_dec.png')
    h.click_at(mw1.SKIING_XY, 10); show('after Skiing'); h.shot('/tmp/fal_ski.png')
    time.sleep(5); show('later')
finally:
    h.close()
