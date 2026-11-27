import sys, time
sys.path.insert(0, 'tools')
from stharness import Hatari

WORK = 'games/in_progress/player-manager/work'
h = Hatari(game_dir='games/in_progress/player-manager/build/game',
           snapshot=None, machine='ste', memsize_kb=1024)
try:
    # Boot through intro to title screen
    for _ in range(4):
        time.sleep(2.5)
        h.keypress(57)
    time.sleep(2.0)

    marker = h.peekl(0xb2ff8)
    mstr = marker.to_bytes(4, 'big').decode('ascii', 'replace')
    print(f'Boot marker at $b2ff8: {marker:#010x} ({mstr!r})', flush=True)
    assert mstr == 'PMOK', f'Patch marker failed: {mstr!r}'

    # Title -> Load Game dialog -> Cancel -> Credits -> Main Menu
    h.click()
    time.sleep(2.0)
    h.rel(150, 120)
    time.sleep(0.3)
    h.click()
    time.sleep(2.0)
    h.click()
    time.sleep(2.0)
    # On Main Menu: move to Demo Game (bottom button)
    h.rel(-150, -60)
    time.sleep(0.3)
    h.shot(f'{WORK}/t2_menu.png')
    h.click()
    time.sleep(3.0)
    h.shot(f'{WORK}/t2_after_demo.png')
    h.savemem(f'{WORK}/t2_after_demo.sav')
    print('Saved t2_after_demo.sav', flush=True)
finally:
    h.close()
