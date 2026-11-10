import re,sys
t=open(sys.argv[1]).read()
v0=int(re.match(r"v0=(\d+)",t).group(1))
# blocks: "pc = $xxxxx" breakpoint hit header
for blk in t.split("CPU breakpoint condition(s) matched")[1:]:
    pcm=re.search(r"pc = \$(\w+)",blk)
    if not pcm: continue
    pc=pcm.group(1)
    vm=re.search(r"#(\d+) \(dec\)",blk)
    if not vm: continue
    cm=re.search(r"> e CycleCounter\n= .*?\$(\w+) \(hex\)",blk)
    vals={}
    for mm in re.finditer(r"> m \$(\w+) (\d+)\n((?:[0-9A-F]{8}: .*\n)+)",blk):
        data=b"".join(bytes.fromhex(l[10:58].replace(" ","")) for l in mm.group(3).strip().split("\n"))
        vals[mm.group(1)]=data[:int(mm.group(2))]
    if "66e6" not in vals: continue
    L=lambda k,o=0:int.from_bytes(vals[k][o:o+4],"big")
    W=lambda k:int.from_bytes(vals[k][:2],"big")
    if pc=="31486" and len(sys.argv)<3 : continue
    print(f"{pc} vbl+{int(vm.group(1))-v0:5d} cyc {int(cm.group(1),16):08x} x{L('66e6'):x} y{L('66e6',4):x} wx{W('66bc')} wy{int.from_bytes(vals['66bc'][2:4],'big')} sav x{L('66f6'):x} y{L('66f6',4):x} f6288={W('6288')} typ{W('6220')} gclk{W('eb8c')} clk{L('b3400')}")
