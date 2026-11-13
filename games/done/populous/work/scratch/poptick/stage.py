import sys, time, os
sys.path.insert(0,"/home/ryan/Code/AtariST/gamebench/games/in_progress/populous/tools")
from populous import Populous
snap=sys.argv[1]
h=Populous(snapshot=Populous.SNAP/f"{snap}.sav")
time.sleep(1.5)
N=h.peekw(h.TURN)+30
out="/tmp/pt/stg_"+snap
os.makedirs(out,exist_ok=True)
sites=[(0xb632,0),(0xb6f4,0),(0xb800,0),(0xb80c,1),(0xb8ec,1),(0xb93a,1),(0xb940,1),(0xb946,1),(0xbb7c,1),(0xbbf8,1),(0xbc02,1)]
h.debug("b all",0.3)
for pc,d in sites:
    f=f"{out}/s{pc:x}.txt"
    open(f,"w").write(f"savebin {out}/m{pc:x}.bin $0 $100000\n")
    h.cmd(f"hatari-debug b pc = ${pc:x} && ($3c506).w = {N+d} :trace :once :file {f}")
    time.sleep(0.2)
h.cmd("hatari-option --fast-forward on")
t=time.time()
while not os.path.exists(f"{out}/mbc02.bin") or os.path.getsize(f"{out}/mbc02.bin")<0x100000:
    if time.time()-t>200: print("timeout"); break
    time.sleep(0.5)
time.sleep(1)
print(h.peekw(h.TURN), "buf", hex(h.peekl(0x3c510)), hex(h.peekl(0x3c50c)))
h.close()
