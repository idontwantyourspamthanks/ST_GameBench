import sys
R=lambda p:open(p,'rb').read()
regs=[('$00000-$086ff low RAM / TOS vars / Gamex hook',0,0x8700),('$08700-$33aff game workspace (cleared at init, screens $900)',0x8700,0x33b00),
 ('$33b00-$75727 game image text+data',0x33b00,0x75728),('$75728-$76b0f dead reloc table / NEBULTIT tail',0x75728,0x76b10),
 ('$76b10-$77ec0 blob zone',0x76b10,0x77ec1),('$77ec1-$7ffff 2nd screen $78000..',0x77ec1,0x80000),
 ('$80000-$b0000 F9 swap area / raw FIC residue',0x80000,0xb0000),('$b0000-$bffff NEPATCH payload',0xb0000,0xc0000),('$c0000-$fffff TOS-state copy / F9 code',0xc0000,0x100000)]
def ex(i):  # expected differences of the patched build
    return (0x3792c<=i<0x37932 or 0x3b0a4<=i<0x3b0aa or 0x3dcf4<=i<0x3dcfa or 0x76c00<=i<0x76c76 or 0xb0000<=i<0xb1000)
def cmp(pa,pb,label):
    a,b=R(pa),R(pb)
    print(label)
    for name,lo,hi in regs:
        d=[i for i in range(lo,hi) if a[i]!=b[i]]
        e=[i for i in d if ex(i)]
        print(f'  {name:62s} differ {len(d):5d}  (of which expected site/blob/payload bytes: {len(e)})')
for ck in ('entry','settle'):
    cmp(f'cmp/stockA/ram_{ck}.bin',f'cmp/stockB/ram_{ck}.bin',f'--- {ck}: stockA vs stockB (control)')
    cmp(f'cmp/stockA/ram_{ck}.bin',f'cmp/patched/ram_{ck}.bin',f'--- {ck}: stockA vs patched')
