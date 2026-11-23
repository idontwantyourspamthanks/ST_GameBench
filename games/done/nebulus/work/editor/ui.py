from ed import *
V=0x77cc0; RS=0x77c80
def menu(h):
    p=L(h,V+4); d=grab(h,p,600,'menu'); n=d[0]; items=[]; i=1
    for _ in range(n):
        a,pr=d[i],d[i+1]; j=i+2
        while d[j]: j+=1
        items.append((a,pr,d[i+2:j].decode('latin1'))); i=j+1
    return items, W(h,V+8)
def K(h,k,n=1,hold=0.2,gap=0.4):
    for _ in range(n): h.key(k,hold=hold); time.sleep(gap)
def fire(h,gap=1.0): K(h,'Control_R',hold=0.35,gap=gap)
def select(h,label,gap=1.0):
    items,sel=menu(h)
    idx=[i for i,(a,p,t) in enumerate(items) if t.startswith(label)]
    assert idx, (label,[t for _,_,t in items])
    d=idx[0]-sel
    if d: K(h,'Down' if d>0 else 'Up',abs(d),gap=0.35)
    items,sel=menu(h); assert sel==idx[0],(label,sel,idx[0])
    fire(h,gap)
def rs(h): return struct.unpack('>20H',grab(h,RS,40,'rs'))
def start(workdir,game,**kw):
    h=Nebulus(workdir=workdir,game=game,**kw)
    assert h.boot_to_title(timeout=160); time.sleep(3)
    return h
def select_i(h,idx,gap=1.0):
    items,sel=menu(h); d=idx-sel
    if d: K(h,'Down' if d>0 else 'Up',abs(d),gap=0.35)
    items,sel=menu(h); assert sel==idx,(sel,idx); fire(h,gap)
def store(h):
    import ovl
    d=grab(h,0xBC000,8192,'store'); return d, (ovl.parse(d) if d[:4]==b'NCMP' else None)
def show(h,tag):
    import ovl
    d,p=store(h)
    if p is None: print(tag,'store: no magic'); return None
    lv,cs=p
    print(tag,'| levels',[(l['name'],l['mission'],l['tower'],l['rows']) for l in lv],'| camps',cs,flush=True)
    return p
