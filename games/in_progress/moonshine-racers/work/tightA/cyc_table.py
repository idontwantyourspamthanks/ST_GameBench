import json, statistics
CYC=160256
rows=[('current default (reference R)','base'),
 ('ta_erase (+ta_init)  [erase+glyph, no face]','ta_init_ta_erase_ta_glyph'),
 ('ta_erase+ta_init+ta_face','ta_init_ta_erase_ta_face'),
 ('speech set: erase+face+glyph (pixel-identical)','ta_init_ta_erase_ta_face_ta_glyph'),
 ('speech set with ta_facestat (VISIBLE)','ta_init_ta_erase_ta_facestat_ta_glyph'),
 ('ta_ymw','ta_ymw'),('ta_rb','ta_rb'),('ta_rb + ta_rb0','ta_rb_ta_rb0'),('ta_nomouse (risk)','ta_nomouse'),
 ('interrupts: rb+ymw+nomouse','ta_rb_ta_ymw_ta_nomouse'),
 ('ALL pixel-identical: speech set + rb + ymw + nomouse (no rb0)','ta_init_ta_erase_ta_face_ta_glyph_ta_rb_ta_ymw_ta_nomouse'),
 ('ALL pixel-identical incl. rb0','ta_init_ta_erase_ta_face_ta_glyph_ta_rb_ta_rb0_ta_ymw_ta_nomouse'),
 ('ALL with ta_facestat (VISIBLE), no rb0','ta_init_ta_erase_ta_facestat_ta_glyph_ta_rb_ta_ymw_ta_nomouse')]
out=[]
for sc,nm in (('race_start','driving (race_start)'),('race_grid','standing (race_grid)')):
    def L(n):
        import os
        p='res/cyc_%s_%s.json'%(sc,n)
        if not os.path.exists(p) and sc=='race_start': p='res/cyc_start_%s.json'%n
        if not os.path.exists(p): return None
        return {x['p']:x for x in json.load(open(p))}
    b=L('base')
    out.append('### %s\n| variant | no speech: mean (n) | delta | VBL/pass | speech: mean (n) | delta | VBL/pass | max pass |\n|---|---:|---:|---:|---:|---:|---:|---:|'%nm)
    for lab,v in rows:
        d=L(v)
        if d is None: continue
        cells=[]
        for sp in (False,True):
            ws=[x['work'] for x in d.values() if x['speech']==sp]
            com=[p for p in d if p in b and b[p]['speech']==sp]
            dl=statistics.mean([b[p]['work']-d[p]['work'] for p in com]) if com else 0
            cells.append((statistics.mean(ws),len(ws),dl))
        mx=max(x['work'] for x in d.values())
        out.append('| %s | %d (%d) | %s | %.3f | %d (%d) | %s | %.3f | %d |'%(lab,cells[0][0],cells[0][1],('-%d'%round(cells[0][2])) if v!='base' else '', cells[0][0]/CYC, cells[1][0],cells[1][1],('-%d'%round(cells[1][2])) if v!='base' else '', cells[1][0]/CYC, mx))
print('\n'.join(out))
