import sys,re,struct
sys.path.insert(0,'tools'); sys.path.insert(0,'../../../tools')
import poppatch as pp
import capstone
md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_BIG_ENDIAN | capstone.CS_MODE_M68K_040)
md.detail=False
pat=re.compile(r'\$(ffff[0-9a-f]{4}|ff[0-9a-f]{4})\b|\$(8[0-9a-f]{3}|9[0-9a-f]{3}|[a-f][0-9a-f]{3})\.w',re.I)
for p,name in ((0,'DEMO'),(1,'POPULOUS')):
    img,tl,dl,offs=pp.program(p)
    text=img[:tl]
    o=0
    print("==",name)
    while o<len(text):
        got=False
        for ins in md.disasm(text[o:o+12],pp.TNOM+o,1):
            got=True
            s=f"{ins.mnemonic} {ins.op_str}"
            if ins.mnemonic.startswith('movep') or re.search(r'\$ff(ff)?[89a-f][0-9a-f]{2}\b',ins.op_str,re.I) or re.search(r'\$[89a-f][0-9a-f]{3}\b',ins.op_str,re.I) and False:
                print(f"{ins.address:06x}: {s}")
            o+=ins.size
        if not got: o+=2
