from ed import *
h=snap('/tmp/ned2')
try:
    time.sleep(2)
    h.debug(f"loadbin {E}t_gemdos.bin $76c00",0.5)
    print(h.debug("m $76c00 8",0.5)[-100:])
    h.debug('w $3dcf4 $4e $b9 $00 $07 $6c $00',0.3)
    time.sleep(6)
    d=grab(h,0x76f00,0x30); print(d.hex(' ',4)); print(d[0x10:0x20])
    h.shot(E+'e2.png')
    os.system(f"cd /tmp/ned2; mdir -i hd.img@@1024 ::")
finally: h.close()
