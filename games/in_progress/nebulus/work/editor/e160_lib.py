from ed import *
import sys, subprocess, shutil
sys.path.insert(0,E)
gd=__import__('pathlib').Path
RS=0x77c80
def mk(game,wd,machine='ste',extra=None):
    kw={}
    if machine=='megaste': kw=dict(machine='megaste',tos=__import__('stharness').TOS['2.06'],memsize_kb=4096)
    return Nebulus(workdir=wd,game=gd(game),extra=extra or [],**kw)
class T:
    def __init__(s,h): s.h=h
    def K(s,k,n=1,hold=0.1,gap=0.3):
        for _ in range(n): s.h.key(k,hold=hold); time.sleep(gap)
    def F(s,gap=0.9): s.K('Control_R',hold=0.35,gap=gap)
    def msg(s):
        a=struct.unpack('>L',grab(s.h,0x77cc0+20,4,'m'))[0]
        if a==0: return None
        d=grab(s.h,a,48,'ms'); return d.split(b'\0')[0].decode('latin1')
    def rs(s): return struct.unpack('>32H',grab(s.h,RS,64,'rs'))
    def insert(s,path):
        s.h.cmd(f"hatari-option --disk-a {path}"); time.sleep(2.0)
    def eject(s):
        s.h.cmd("hatari-option --disk-a ''"); time.sleep(1.5)
    def store(s): return grab(s.h,0xBC000,8192,'store')
    def alive(s):
        v0=s.h.vbl(); time.sleep(1.0); return s.h.vbl()-v0>20
