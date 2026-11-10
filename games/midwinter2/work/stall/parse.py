import re,sys
t=open(sys.argv[1]).read()
v0=int(re.match(r"v0=(\d+)",t).group(1))
blocks=t.split("Reading debugger commands")[1:]
rows=[]
def hexb(s): return bytes.fromhex(re.sub(r"\s+","",s))
for b in blocks:
    m=re.search(r"#(\d+) \(dec\)",b); 
    if not m: continue
    vbl=int(m.group(1))
    vals={}
    for mm in re.finditer(r"> m \$(\w+) (\d+)\n((?:[0-9A-F]{8}: .*\n)+)",b):
        data=b""
        for ln in mm.group(3).strip().split("\n"):
            data+=bytes.fromhex(ln[10:10+48].replace(" ",""))
        vals[mm.group(1)]=data
    if len(vals)<12: continue
    D=vals["b42e0"]
    w=lambda d,o:int.from_bytes(d[o:o+2],"big")
    l=lambda d,o:int.from_bytes(d[o:o+4],"big")
    rows.append(dict(vbl=vbl-v0,clk=l(vals["b3400"],0),last=l(D,0),acc=w(D,4),ph=w(D,6),sub=w(D,8),hold=w(D,10),skip=w(D,12),
        x=l(vals["66e6"],0),y=l(vals["66e6"],4),typ=w(vals["6220"],0),m40=w(vals["40b6"],0),ctx=w(vals["700a"],0),gate=w(vals["6298"],0),
        gclk=w(vals["eb8c"],0),cd=w(vals["6290"],0),route=w(vals["764c"],0),spd=w(vals["6772"],0),hdg=w(vals["6742"],0)))
prev=None
print("n",len(rows))
for r in rows:
    gap=r["vbl"]-prev["vbl"] if prev else 0
    flag="  <<<" if gap>20 else ""
    if len(sys.argv)>2 or flag: 
        print(f'{r["vbl"]:5d} gap{gap:4d} clk{r["clk"]:6d} last{r["last"]:6d} acc{r["acc"]:4d} ph{r["ph"]} sub{r["sub"]} hold{r["hold"]} skip{r["skip"]} x{r["x"]:x} y{r["y"]:x} typ{r["typ"]} m40{r["m40"]} ctx{r["ctx"]} gate{r["gate"]} gclk{r["gclk"]} cd{r["cd"]} route{r["route"]:x} spd{r["spd"]} hdg{r["hdg"]:x}{flag}')
    prev=r
