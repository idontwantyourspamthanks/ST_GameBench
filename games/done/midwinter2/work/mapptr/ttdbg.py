import sys, time
from pathlib import Path
ROOT = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2')
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools')
from mw2harness import Hatari
from stharness import MACHINE_TOS
src, machine, mem = sys.argv[1:4]
h = Hatari(snapshot=str(ROOT/'work/mapptr'/src/'map.sav'), machine=machine, tos=MACHINE_TOS[machine], memsize_kb=int(mem), game_dir=ROOT/'build/MW2MapPtr_stock', extra=['--mmu','true'] if machine=='tt' else None)
try:
    time.sleep(3)
    for cmd in ('m $770e 8','m $67a6 8','m $6306 $30','m $62fa $18','m $ff8200 $10','info video'):
        print(cmd); print(h.debug(cmd, 1.0))
    print(h.shot(str(ROOT/'work/mapptr/ttdbg.png')))
    h.dump(str(ROOT/'work/mapptr/ttdbg_ram.bin'), 0, 0x80000); time.sleep(2)
finally:
    h.close()
