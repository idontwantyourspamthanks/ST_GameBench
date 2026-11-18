import sys; sys.path.insert(0,'work/hud')
from analyze import *
from mktables import classes
ROWS=[('thermometer','`efc6`',['efc6'],'on change of `$10ba`, 2 redraws per change','752','yes (clear 0,18-31,64 once)'),
('engine-fire puff','`f1c0`+`f134`',['f1c0','f134'],'only while `$10ba>=35`','52','yes'),
('minimap box fill','`f214`',['f214'],'every pass','1,152','yes (clear once)'),
('minimap','`f22c`',['f22c'],'every pass','568','yes (clear once)'),
('score','`f3b6`',['f3b6'],'when `$11c2` changes (every pass while driving), 2x','336','yes (clear once)'),
('position no.','`f430`',['f430'],'when `$10ca` changes, 2x','224','yes'),
('stopwatch dial','`f53c`',['f53c'],'whole-long compare: every pass while the clock runs','496','yes (clear once)'),
('message ticker','`11ef0`',['11ef0'],'1 glyph/pass while typing (+1 repeat), 2 x box erase at the end','40-48 per glyph; 4,704 erase','**NO** (race-end state machine); drawing only'),
('talking face','`f90c`',['f90c'],'every pass while a message is active','768','yes'),
('turbo-fuel cup','`f620`',['f620'],'every pass (road erases it)','328','yes, clean'),
('gear lever','`f76a`',['f76a'],'every pass (road erases it)','172','yes, clean'),
('speedometer','`f7f0`',['f7f0'],'every pass (road erases it)','588','yes, clean')]
def block(scene,title,cls):
    p,s=load(f'skip_{scene}_stock'); c=classes(p,s)
    ks={cl:[k for k in c if c[k]==cl] for cl in cls}
    W={cl:sum(p[k]['work'] for k in ks[cl])/len(ks[cl]) for cl in cls}
    print(f"\n**{title}** (pass work: "+', '.join(f"{cl} {W[cl]:,.0f} (n={len(ks[cl])})" for cl in cls)+")\n")
    print('| element | routine | '+' | '.join(f"cycles/pass {cl} (% of pass)" for cl in cls)+' | redraw rule | bytes written | safe to skip? |')
    print('|---|---|'+'---:|'*len(cls)+'---|---:|---|')
    tot={cl:0 for cl in cls}
    for name,rt,calls,rule,by,safe in ROWS:
        vals=[]
        for cl in cls:
            v=sum(sum(p[k]['stage'].get(n,0) for k in ks[cl])/len(ks[cl]) for n in calls); tot[cl]+=v; vals.append(f"{v:,.0f} ({100*v/W[cl]:.1f} %)")
        print(f"| {name} | {rt} | "+' | '.join(vals)+f" | {rule} | {by} | {safe} |")
    print('| **HUD total** | 13 calls | '+' | '.join(f"**{tot[cl]:,.0f} ({100*tot[cl]/W[cl]:.1f} %)**" for cl in cls)+' | | | |')
print("### Master table per scene (stock game; cycles per pass, class means; the ticker's two 34.9 k erase passes per message are not in these means)\n")
block('race_start','race_start (driving)',['none','typing'])
block('race_grid','race_grid (standing, time-out state)',['none','typing'])
