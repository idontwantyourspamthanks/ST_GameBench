import struct
TS=4608
def ts_off(ts):
    return ((ts*2) if ts<80 else ((ts-80)*2+1))*TS
class FFA:
    def __init__(s,path):
        s.path=path; s.b=bytearray(open(path,'rb').read())
        s.dir=ts_off(1)
    def entry(s,k):
        o=s.dir+8+8*k
        ck,off,ts=struct.unpack('>HHB',s.b[o:o+5]); ln=int.from_bytes(s.b[o+5:o+8],'big')
        return dict(o=o,ck=ck,off=off,ts=ts,len=ln)
    def read(s,k):
        e=s.entry(k); out=bytearray(); pos=e['off']; ts=e['ts']; need=e['len']+e['off']
        got=0
        while got<need:
            out+=s.b[ts_off(ts):ts_off(ts)+TS]; ts+=1; got+=TS
        return bytes(out[e['off']:e['off']+e['len']])
    def write(s,k,data):
        e=s.entry(k); assert len(data)==e['len']
        full=bytearray()
        ts=e['ts']; n=(e['off']+e['len']+TS-1)//TS
        for i in range(n): full+=s.b[ts_off(ts+i):ts_off(ts+i)+TS]
        full[e['off']:e['off']+e['len']]=data
        for i in range(n): s.b[ts_off(ts+i):ts_off(ts+i)+TS]=full[i*TS:(i+1)*TS]
    @staticmethod
    def xor(d):
        c=0
        if len(d)%2: d=d+b'\0'
        for i in range(0,len(d),2): c^=(d[i]<<8)|d[i+1]
        return c
if __name__=='__main__':
    import sys
    f=FFA(sys.argv[1])
    for k in range(12):
        e=f.entry(k)
        if e['len']==0 and k>10: continue
        d=f.read(k) if e['len'] else b''
        print(k,{a:hex(v) for a,v in e.items()}, 'xor=%04x'%FFA.xor(d))
