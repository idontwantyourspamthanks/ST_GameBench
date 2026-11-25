import sys, json; sys.path.insert(0,'.')
from collections import defaultdict
RES="/tmp/pmww1prof/res/"
NW = {0x13da8:"tick/pass head ($1359a)",0x13db4:"$1359a",0x13dba:"$576a",0x13dc0:"$d712",0x13dc6:"$3276",0x13e04:"VBL wait $e04",0x13e0a:"window copy $13a94",0x13e18:"$18570 (tooltip slot)",0x13e1e:"landscape+objects $fc78",0x13e24:"$1b90a weather",0x13e2a:"$1853a HUD",0x13e30:"$17462 HUD/army",0x13e36:"$158b2 men sim",0x13e3c:"$6396 UI",0x13e42:"$74e0 UI",0x13e6a:"$d62a",0x13e70:"$6c16",0x145e2:"flip $e0e",0x145e8:"$1af32"}
NP = {0x13020:"tick head",0x13040:"$127e6",0x13046:"$6522",0x1304C:"$d322",0x13052:"$3e06",0x13090:"VBL wait $1870",0x13096:"window copy $12ce0",0x130A4:"$178ae",0x130AA:"landscape+objects $f898",0x130B0:"$1abaa weather",0x130B6:"$17878 HUD",0x130BC:"$165b2 HUD/army",0x130C2:"$14b62 men sim",0x130C8:"$6a3a UI",0x130CE:"$7a56 UI",0x130F6:"$d23a",0x130FC:"$7202",0x1386C:"flip $187a",0x13872:"$1a276"}
# group into master-comparable stages
GW = {"logic":[0x13da8,0x13db4,0x13dba,0x13dc0,0x13dc6],"VBL wait":[0x13e04],"window copy":[0x13e0a],"landscape+objects":[0x13e18,0x13e1e],"HUD/UI/men/weather/rest":[0x13e24,0x13e2a,0x13e30,0x13e36,0x13e3c,0x13e42,0x13e6a,0x13e70,0x145e2,0x145e8]}
GP = {"logic":[0x13020,0x13040,0x13046,0x1304C,0x13052],"VBL wait":[0x13090],"window copy":[0x13096],"landscape+objects":[0x130A4,0x130AA],"HUD/UI/men/weather/rest":[0x130B0,0x130B6,0x130BC,0x130C2,0x130C8,0x130CE,0x130F6,0x130FC,0x1386C,0x13872]}
def stage(g,s,mhz):
    d=json.load(open(f"{RES}{g}_{s}_{mhz}.json")); recs=d["recs"]
    G=GW if g=="ww1" else GP; copy=0x13e0a if g=="ww1" else 0x13096
    acc=defaultdict(int); tot=0
    for a,b in zip(recs,recs[1:]):
        dd=(b[1]-a[1])&0xFFFFFFFF
        if dd>8_000_000: continue
        acc[a[0]]+=dd; tot+=dd
    n=sum(1 for r in recs if r[0]==copy)
    out={k:sum(acc[p] for p in v) for k,v in G.items()}
    return out,tot,n
if __name__=="__main__":
  for mhz in (8,16):
    for g,sn in (("ww1",["map_idle","get_men"]),("pm",["map_idle","get_men","battle_320"])):
      for s in sn:
        o,tot,n=stage(g,s,mhz)
        print(f"{g} {s} {mhz}MHz rendered passes {n} total {tot/n:.0f} cyc/pass: "+" | ".join(f"{k} {v/n:.0f} ({100*v/tot:.1f}%)" for k,v in o.items()))
