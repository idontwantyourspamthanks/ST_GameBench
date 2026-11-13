import sys, json, types
exec(open('/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2/work/scratch/disks/matrix.py').read().split("if __name__=='__main__':")[0])
def retarget(h, machine):
    if machine=='tt':   dx,dy,home=-96,-58,(0,0)
    elif machine=='falcon': dx,dy,home=-96+2,-58+64,(2,64)
    else: return
    def _click(self,x,y,wait=4.0):
        self.goto(x+dx,y+dy,home_xy=home); self.click(hold=0.4); time.sleep(wait)
    h._click=types.MethodType(_click,h)
_run=run
def run2(img,tag,mem,kind,machine,tos):
    # monkeypatch boot2 to retarget clicks
    global boot2
    ob=boot2
    def b2(*a,**k):
        if machine=='tt': k['extra']=['--mmu','true']
        h=ob(*a,**k); retarget(h,machine); return h
    boot2=b2
    try:
        return _run(img,tag,mem,kind,machine,tos)
    finally:
        boot2=ob
if __name__=='__main__':
    img,tag,mem,kind,machine,tos=sys.argv[1:7]
    r=run2(img,tag,int(mem),kind,machine,tos)
    print('RESULT',json.dumps(r))
