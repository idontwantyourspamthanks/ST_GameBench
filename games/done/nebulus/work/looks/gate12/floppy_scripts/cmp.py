import sys, json, subprocess
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor')
import ovl
files=sys.argv[1:]
r=subprocess.run(['bin/rails','runner','/tmp/ng12fl/x/dump.rb']+files,cwd='/home/ryan/Code/dadprg/api',capture_output=True,text=True,env={**__import__('os').environ,'RAILS_ENV':'test'})
ruby=json.loads(r.stdout)
bad=0
for f,rb in zip(files,ruby):
    lv,camps=ovl.parse(open(f,'rb').read())
    assert len(lv)==len(rb['levels']),(f,'level count')
    for a,b in zip(lv,rb['levels']):
        ok = (a['grid']==b['grid'] and a['flags']==b['flags'] and a['tower']==b['tower'] and a['rows']==b['rows'] and a['name'].strip()==b['name'] and a['time']==b['time_bcd'] and a['mission']==b['mission'])
        cs = b['colours'] if b['colours'] else b['tower']+1
        # expected from the game semantic: colour nibble (flags>>4) else tower+1 ; enemy nibble else (tower&3)+1
        ok2 = b['colour_scheme']==( (a['flags']>>4) or a['tower']+1) and b['eye_design']==((a['flags']&15) or (a['tower']&3)+1)
        cells={}
        for c in range(16):
            for rr in range(a['rows']):
                v=a['grid'][c][rr]
                if v: cells[v]=cells.get(v,0)+1
        print(('PASS' if ok and ok2 else 'FAIL'), f.split('/')[-1], a['name'], f"rows={a['rows']} tower={a['tower']} flags={a['flags']:#04x} size={a['size']} ruby(tower={b['tower']} flags={b['flags']:#04x} colour_scheme={b['colour_scheme']} eye_design={b['eye_design']}) grid_equal={a['grid']==b['grid']} semantics={ok2}", {hex(k):v for k,v in sorted(cells.items())})
        bad+= not (ok and ok2)
    pl=[(n,e) for n,e in camps]
    rpl=[(p['name'],p['entries']) for p in rb['playlists']]
    print('  campaigns',pl,'| ruby',[(n,len(e)) for n,e in rpl])
print('FAILS',bad)
