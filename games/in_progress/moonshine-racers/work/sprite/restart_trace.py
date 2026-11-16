import sys,time,re
from pathlib import Path
sys.path.insert(0,'tools')
from msr import Moonshine
import msrabtest as ab
snap=sys.argv[1]; wait=float(sys.argv[2])
h=Moonshine(snapshot=ab.snap_path(snap)); time.sleep(2)
pcs=[0xd8e0,0xd8ca,0xdd1c,0xdd18,0xdeee,0x7be0,0x7c0c,0x719c,0x7368,0x73e6,0x769a,0x7d26,0x842c,0xd910,0xd930,0x7600,0x75a4]
for pc in pcs:
    (h.R/f"r_{pc:x}.txt").write_text("e VBL\nm $100e 2\nm $1021 1\n")
h.debug("b all",0.3); n0=len(h._logtext())
# $796a first hit after each of the others is too frequent: log it with counter only when frame ctr is small
for pc in pcs:
    h.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {h.R}/r_{pc:x}.txt"); time.sleep(0.1)
time.sleep(wait)
h.debug("b all",1); log=h._logtext()[n0:]; h.close()
parts=re.split(r"\n\t(pc = \$[0-9a-f]+) :trace :file [^\n]*\nReading debugger commands from[^\n]*\n",log)
for i in range(1,len(parts)-1,2):
    body=parts[i+1]
    v=re.findall(r"#(\d+) \(dec\)",body); m=re.search(r"0000100E: ([0-9a-f]{2}) ([0-9a-f]{2})",body); m2=re.search(r"00001021: ([0-9a-f]{2})",body)
    print(parts[i], 'vbl',v[0] if v else None,'$100e',int(m.group(1)+m.group(2),16) if m else None,'$1021',m2.group(1) if m2 else None)
