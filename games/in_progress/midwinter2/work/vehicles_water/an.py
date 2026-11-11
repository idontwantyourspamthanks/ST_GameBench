import pickle,sys
from vw import *
sys.argv=[sys.argv[0]]+sys.argv[1:]
exec(open('cmp.py').read().split("def main")[0])
ctl,pat=pickle.load(open('logs/%s.pkl'%sys.argv[1],'rb'))
for k in range(1,min(len(ctl),len(pat))):
    d=diff(ctl[k],pat[k])
    npc=[a for a in d if 0x3532<=a<0x3cee]; oth={a:v for a,v in d.items() if not 0x3532<=a<0x3cee}
    print(k,'npc words differing:',len(npc),sorted({(a-0x3532)//0x42 for a in npc}),' other:',' '.join('%s:%d/%d'%(name(a),v[0],v[1]) for a,v in sorted(oth.items()))[:300])
