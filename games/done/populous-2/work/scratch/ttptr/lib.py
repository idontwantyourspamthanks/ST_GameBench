import sys, time
from pathlib import Path
G="/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2"
sys.path[:0]=[G+"/tools","/home/ryan/Code/AtariST/gamebench/tools"]
from populous2 import Populous2
from PIL import Image, ImageChops
OUT=Path(G+"/work/scratch/ttptr")
def mk(build, mach, mem=4096, extra=()):
    ex=(["--mmu","true"] if mach=="tt" else [])+list(extra)
    return Populous2(game_dir=build, machine=mach, memsize_kb=mem, extra=ex)
def sc(h):  # scale ST->png
    return 2
def sample(h, tag, n, mov, dt=1.0):
    """n shots; if mov, nudge host mouse between shots. returns list of (png,px,py)"""
    r=[]
    for i in range(n):
        if mov:
            h.rel(30 if i%2==0 else -30, 14 if i%2==0 else -14, 4)
        time.sleep(dt)
        p=h.shot(str(OUT/f"{tag}_{i:02d}.png"))
        px,py=h.peekw(0x393fa),h.peekw(0x393fc)
        r.append((str(p),px,py))
    return r
def analyse(r, tag, pic_off=(0,0), mul=2):
    ims=[Image.open(p).convert("RGB") for p,_,_ in r]
    res=[]
    for i,(p,x,y) in enumerate(r):
        box=(pic_off[0]+x*mul, pic_off[1]+y*mul, pic_off[0]+(x+16)*mul, pic_off[1]+(y+16)*mul)
        box=(max(box[0],0),max(box[1],0),min(box[2],ims[i].width),min(box[3],ims[i].height))
        cands=[j for j,(q,a,b) in enumerate(r) if abs(a-x)>=20 or abs(b-y)>=20]
        if not cands: res.append((i,x,y,None)); continue
        # use the ref with the smallest total diff elsewhere? take min diff over refs (conservative: absent if any ref equals)
        d=min(sum(1 for px in ImageChops.difference(ims[i].crop(box),ims[j].crop(box)).getdata() if px!=(0,0,0)) for j in cands)
        res.append((i,x,y,d))
    vis=sum(1 for *_,d in res if d)
    print(tag, "visible (region differs from a pointer-elsewhere shot) %d/%d"%(vis,len(res)), [ (x,y,d) for _,x,y,d in res])
    return res

def goto_st(h, x, y):
    h.home(); h.rel(2*x, 2*y, 10); time.sleep(0.4)
    return h.peekw(0x393fa), h.peekw(0x393fc)

def region_diff(im, ref, x, y, mul=2, off=(0,0)):
    box=(off[0]+x*mul-2, off[1]+y*mul-2, off[0]+(x+16)*mul+2, off[1]+(y+16)*mul+2)
    box=(max(box[0],0),max(box[1],0),min(box[2],im.width),min(box[3],im.height))
    return sum(1 for p in ImageChops.difference(im.crop(box),ref.crop(box)).getdata() if p!=(0,0,0))

def pointer_test(h, tag, P=(100,100), Q=(240,60), n=10, moving_n=10, off=(0,0), settle=0.3, dt=1.0):
    """still: pointer parked at P, n shots; ref region from a shot with the pointer at Q. moving: pointer stepped to 10 positions."""
    q=goto_st(h,*Q); time.sleep(1.0)
    refp=h.shot(str(OUT/f"{tag}_ref.png")); ref=Image.open(refp).convert("RGB")
    p=goto_st(h,*P); time.sleep(1.0)
    still=[]
    for i in range(n):
        time.sleep(dt)
        f=h.shot(str(OUT/f"{tag}_still{i:02d}.png")); im=Image.open(f).convert("RGB")
        still.append(region_diff(im,ref,*p,off=off))
    mov=[]
    for i in range(moving_n):
        x=60+i*13; y=60+(i%4)*25
        h.rel(2*(x-p[0]) if False else 0,0,1)
        q2=goto_st(h,x,y); time.sleep(settle)
        # reference for this position is the ref shot unless it overlaps Q's pointer
        f=h.shot(str(OUT/f"{tag}_mov{i:02d}.png")); im=Image.open(f).convert("RGB")
        mov.append((q2, region_diff(im,ref,*q2,off=off)))
    vs=sum(1 for d in still if d>10); vm=sum(1 for _,d in mov if d>10)
    print(f"RESULT {tag}: pointer at {p}: still visible {vs}/{len(still)} diffs {still}; moving visible {vm}/{len(mov)} {mov}", flush=True)
    return vs,len(still),vm,len(mov)

def rdb(h, a, n):
    import p2tick as TK
    return TK.rdb(h, a, n)

def expected(h):
    """pointer pixels from RAM: [(x,y,idx)] (ST coords) + palette words"""
    x,y=h.peekw(0x393fa),h.peekw(0x393fc)
    shp=h.peekw(0x11d50)
    sh=rdb(h,0x682d0+shp,128)
    pal=[h.peekw(0xff8240+2*i)&0xfff for i in range(16)]
    px=[]
    for r in range(16):
        w=[int.from_bytes(sh[r*8+2*p:r*8+2*p+2],"big") for p in range(4)]
        for c in range(16):
            idx=sum(((w[p]>>(15-c))&1)<<p for p in range(4))
            m=any((w[p]>>(15-c))&1 for p in range(4))
            if m and y+r<200: px.append((x+c,y+r,idx))
    return (x,y,shp),px,pal

def ptr_score(h, png, off=(0,0), mul=2):
    """class-consistency of the screenshot at the pointer's mask pixels (RAM shape/pos): returns (frac_ok, distinct_modal_colours, classes)"""
    (x,y,shp),px,_=expected(h)
    return ptr_score_at(png,(x,y,shp),px,off,mul)

def safeshot(h, path, tries=4):
    for _ in range(tries):
        f=h.shot(path); time.sleep(0.4)
        try:
            Image.open(f).load(); return f
        except Exception:
            time.sleep(0.5)
    return f

def openimg(png):
    for _ in range(20):
        try:
            im=Image.open(png); im.load(); return im.convert("RGB")
        except Exception:
            time.sleep(0.3)
    raise RuntimeError("bad png "+str(png))

def ptr_score_at(png,pos,px,off=(0,0),mul=2):
    im=openimg(png)
    cls={}
    for (a,b,i) in px:
        X,Y=off[0]+a*mul,off[1]+b*mul
        if X<im.width and Y<im.height:
            cls.setdefault(i,{}); c=im.getpixel((X,Y)); cls[i][c]=cls[i].get(c,0)+1
    tot=sum(sum(v.values()) for v in cls.values())
    if not tot: return 0.0,0,0
    ok=sum(max(v.values()) for v in cls.values())
    modal={max(v,key=v.get) for v in cls.values()}
    return ok/tot,len(modal),len(cls)

def visible(sc): return sc[0]>=0.95 and sc[1]>=max(2,sc[2])

def stage(h, name, P, still=12, moving=12, mov=None, dt=1.0, off=(0,0), log=None):
    """still: pointer parked at P, `still` shots ~dt apart (>=20 s); moving: the host pointer stepped between positions (settle 0.3 s)"""
    p=goto_st(h,*P); time.sleep(0.8)
    res=[]
    for i in range(still):
        time.sleep(dt)
        f=safeshot(h,str(OUT/f"{name}_s{i:02d}.png"))
        sc=ptr_score(h,f,off); res.append(("s",p,sc))
    mov=mov or [(P[0]+((i*29)%80)-40, P[1]+((i*17)%60)-30) for i in range(moving)]
    for i,(x,y) in enumerate(mov[:moving]):
        q=goto_st(h,x,y); time.sleep(0.3)
        f=safeshot(h,str(OUT/f"{name}_m{i:02d}.png"))
        sc=ptr_score(h,f,off); res.append(("m",q,sc))
    vs=sum(1 for k,_,s in res if k=="s" and visible(s)); vm=sum(1 for k,_,s in res if k=="m" and visible(s))
    line=f"STAGE {name}: still {vs}/{still} moving {vm}/{len(mov[:moving])}  scores still {[round(s[0],2) for k,_,s in res if k=='s']} moving {[round(s[0],2) for k,_,s in res if k=='m']}"
    print(line,flush=True)
    return vs,still,vm,len(mov[:moving])

def stage_fast(h, name, P, n=40, dt=0.2, off=(0,0)):
    p=goto_st(h,*P); time.sleep(1.0)
    pos,px,_=expected(h)
    res=[]
    for i in range(n):
        time.sleep(dt)
        f=safeshot(h,str(OUT/f"{name}_f{i:02d}.png"))
        res.append(ptr_score_at(f,pos,px,off))
    vs=sum(1 for s in res if visible(s))
    print(f"FAST {name}: pointer {pos} visible {vs}/{n} scores {[round(s[0],2) for s in res]}",flush=True)
    return vs,n
