import sys, re, struct
sys.path.insert(0,'../../../tools')
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools')
import m68dis as M
ram=open('work/dumps/ram_race_start.bin','rb').read()
WR1={'clr','addq','subq','neg','not','st','sf','bset','bclr','bchg','negx','nbcd','scc','scs','seq','sne','sge','sgt','slt','sle','shi','sls','spl','smi','svc','svs','asl','asr','lsl','lsr','rol','ror','roxl','roxr'}
RO={'cmp','cmpi','cmpa','tst','btst','jmp','jsr','pea','lea','chk'}
def an(entry, seen=None, depth=0, calls=None):
    seen=seen if seen is not None else set()
    W=set();R=set();C=[]
    stack=[entry]
    while stack:
        a=stack.pop()
        while True:
            if a in seen: break
            seen.add(a)
            ins=next(M.md.disasm(ram[a:a+10],a),None)
            if ins is None: break
            mn=ins.mnemonic.split('.')[0]; ops=ins.op_str
            parts=[p.strip() for p in re.split(r',(?![^(]*\))',ops)] if ops else []
            def addr(p):
                m=re.fullmatch(r'\$([0-9a-f]+)\.([wl])',p)
                return int(m.group(1),16) if m else None
            if mn in('jsr','bsr'):
                t=None
                m=re.match(r'\$([0-9a-f]+)',ops)
                if m and len(parts)==1 and not ops.startswith('('): t=int(m.group(1),16)
                if t: C.append(t); stack.append(t)
                else: C.append(('ind',ops,a))
            else:
                if parts:
                    last=parts[-1]
                    ad=addr(last)
                    if ad is not None and ad<0x7000:
                        if mn in WR1 or (len(parts)>=2 and mn not in RO): W.add((ad,mn,a))
                        else: R.add((ad,a))
                    for p in parts[:-1] if len(parts)>1 else []:
                        ad=addr(p)
                        if ad is not None and ad<0x7000: R.add((ad,a))
                    if len(parts)==1 and ad is not None and mn in RO: R.add((ad,a))
            if mn in('rts','rte'): break
            if mn=='jmp': 
                break
            if mn.startswith('b') and mn not in('bsr','btst','bset','bclr','bchg','bfextu') and len(ins.mnemonic)<=5:
                m=re.match(r'\$([0-9a-f]+)',ops)
                if m:
                    t=int(m.group(1),16)
                    if mn=='bra': a=t; continue
                    stack.append(t)
            a+=ins.size
    return W,R,C
if __name__=='__main__':
    for e in sys.argv[1:]:
        e=int(e,16)
        W,R,C=an(e)
        print(f"== {e:06x}  calls {[hex(c) if isinstance(c,int) else c for c in C][:40]}")
        ws={}
        for ad,mn,a in W: ws.setdefault(ad,[]).append(f"{a:x}")
        print(" W:", ' '.join(f"${ad:x}({','.join(v[:2])})" for ad,v in sorted(ws.items())))
