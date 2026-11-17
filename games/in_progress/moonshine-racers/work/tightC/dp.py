"""python3 dp.py NAME START END : disassembly with per-pass cycles and executions per pass"""
import sys, subprocess, re
G='/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers'
sys.path.insert(0, G+'/tools')
import msrprof as P
name,s,e=sys.argv[1],sys.argv[2],sys.argv[3]
prof=P.load(f'{G}/work/tightC/res/prof_{name}.txt'); fr=prof[0xd1ca][1]
out=subprocess.run([sys.executable,G+'/../../../tools/m68dis.py',f'{G}/work/tightC/res/ram_{name}.bin',s,'--end',e],capture_output=True,text=True).stdout
for l in out.splitlines():
    m=re.match(r'([0-9a-f]{6}):',l)
    if m:
        a=int(m.group(1),16); c,n=prof.get(a,(0,0))
        print(f'{c/fr:7.0f} {n/fr:6.2f} {l}')
    else: print(' '*15+l)
