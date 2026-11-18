from ed import *
h=snap('/tmp/ned9',game=__import__('pathlib').Path(E+'gd'))
try:
    time.sleep(3)
    h.debug(f"loadbin {E}t_save.bin $76c00",0.5)
    h.debug(f"loadbin {E}buf.bin $77000",0.5)
    h.debug('w $3dcf4 $4e $b9 $00 $07 $6c $00',0.3)
    for i in range(12):
        time.sleep(2)
        d=grab(h,0x76f00,0x20)
        print(i,'flag',d[:2].hex(),'res',d[0x10:0x1c].hex(' ',4),'vbl',h.vbl(),flush=True)
        if d[:2]==b'\x00\x02': break
    time.sleep(3)
    print('after: vbl',h.vbl(), 'timer', grab(h,0x3ad98,6).hex(), 'hz200',L(h,0x4ba),'vec70',hex(L(h,0x70)),hex(L(h,0x118)))
    h.shot(E+'e9.png')
    print(h.debug('r',0.8)[-400:])
finally: h.close()
os.system("cd /tmp/ned9; mdir -i hd.img@@1024 ::NEBLEVEL.OVL; mcopy -n -i hd.img@@1024 ::NEBLEVEL.OVL /tmp/ned9/out.ovl; xxd /tmp/ned9/out.ovl | head -8")
