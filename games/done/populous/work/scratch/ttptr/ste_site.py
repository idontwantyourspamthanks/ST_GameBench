"""STE 1 MB cold boot of the packaged HD build: is the flip's base write at $16f32 still the original bytes?"""
import sys, time
from pathlib import Path
GAME = Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous")
sys.path.insert(0, str(GAME / "tools"))
import poptick as pt
from populous import Populous
from stharness import TOS
h = Populous(game_dir=GAME / "build/dist_hd", machine="ste", tos=TOS["1.62"], memsize_kb=1024)
try:
    ok = pt.cold_to_play(h, "ste")
    print("MACHV", pt.rdb(h, 0xB300C, 4).hex()); print("in_play", ok, "marker", pt.rdb(h, 0xB3004, 4), "$16f32:", pt.rdb(h, 0x16F32, 8).hex(), "(original e04823c0ffff8200)", "$16d66:", pt.rdb(h, 0x16D66, 10).hex(), "(original 6c06427900016d264e75)", "blob $b8000:", pt.rdb(h, 0xB8000, 8).hex())
finally:
    h.close()
