import sys, time
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/jagpad')
from jt import *
from stharness import MACHINE_TOS
for snap, mach, mem in (('fire_ste14fix_foot.sav','ste',1024),('fire_tt14fix_foot.sav','tt',4096)):
    h = Hatari(snapshot=str(SNAP/snap), machine=mach, tos=MACHINE_TOS[mach], memsize_kb=mem, extra=['--joy1','none']+(['--mmu','true'] if mach=='tt' else []))
    try:
        time.sleep(5)
        print(snap, 'MWPO', memb(h,0xb2ff8,4), 'site $315d0', memb(h,0x315d0,6).hex(), 'blob $b7e00', memb(h,0xb7e00,6).hex(), 'type', w(h,0x6220), 'view', w(h,0x700a))
    finally: h.close()
