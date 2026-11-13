import sys
from lib import *
from stharness import TOS
build,mach,mem,tos=sys.argv[1],sys.argv[2],int(sys.argv[3]),sys.argv[4]
h=Populous2(game_dir=build,machine=mach,tos=TOS[tos],memsize_kb=mem,extra=(["--mmu","true"] if mach=="tt" else []))
try:
    ok=h.boot_to_game()
    t0=h.peekw(h.TURN); time.sleep(3); t1=h.peekw(h.TURN)
    b=rdb(h,0x1c16,6)
    print(f"COLD {mach} {mem}KB TOS {tos}: in_play={ok} marker={h.marker()!r} turn {t0}->{t1} site $1c16={b.hex()} TT_F($86fa0)={rdb(h,0x86fa0,1).hex()} $202e={h.peekl(0x202e):#x}")
    h.shot(str(OUT/f"cold_{mach}_{mem}.png"))
finally: h.close()
