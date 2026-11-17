import re
def rd(p): return open(p, errors='replace').read().rstrip()
cyc = rd('res/cyc_table.md'); hz = rd('res/hz_table.md')
state = rd('res/state_cmp.txt')
state = '\n'.join(l for l in state.splitlines())
prof_ref = rd('res/prof_ref.txt'); prof_isr = rd('res/prof_isr.txt')
unit = rd('res/unit_ym_rb.txt'); glyph = rd('res/unit_glyph.txt'); neg = rd('res/neg_controls.txt')
emu = rd('res/emu_all_x3.txt'); emu = '\n'.join(l for l in emu.splitlines() if not l.startswith('  RAM $08e') and not l.startswith('  RAM $0d') and not l.startswith('  RAM $0ed') and not l.startswith('  RAM $0f9') and not l.startswith('  RAM $120') and not l.startswith('  RAM $14f'))
rbc = rd('res/rb_cmp_rb.txt'); rbc0 = rd('res/rb_cmp_rb0.txt')
joy = rd('res/joy.log'); cold = rd('res/cold.log')
pix = rd("res/pix_hatari.txt"); pixn = rd("res/pix_hatari_neg.txt") if __import__("os").path.exists("res/pix_hatari_neg.txt") else "(negative-control run still pending when this note was written: res/pix_hatari_neg.txt)"
bis = rd('res/bisect.log')
T = open('note_template.md').read()
for k, v in dict(CYC=cyc, HZ=hz, STATE=state, PROFREF=prof_ref, PROFISR=prof_isr, UNIT=unit, GLYPH=glyph, NEG=neg, EMU=emu, RBC=rbc, RBC0=rbc0, JOY=joy, COLD=cold, PIX=pix, PIXN=pixn, BIS=bis).items():
    T = T.replace('{{%s}}' % k, v)
open('../notes/tighten_a.md', 'w').write(T)
print(len(T))
