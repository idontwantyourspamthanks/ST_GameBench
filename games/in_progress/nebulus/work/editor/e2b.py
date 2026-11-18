from ed import *
h=snap('/tmp/ned2')
try:
    time.sleep(2)
    h.debug(f"loadbin {E}t_gemdos.bin $76c00",0.5)
    h.debug('w $3dcf4 $4e $b9 $00 $07 $6c $00',0.3)
    time.sleep(5)
    print(h.debug('r',1.0))
    for a,n in [(0x84,4),(0x4a2,4),(0x4ba,4),(0x4c2,4),(0x472,12)]:
        print(hex(a),grab(h,a,n).hex(' '))
    print(h.debug('m $a00 32',0.5))
    print(open('/tmp/ned2/log.txt').read()[-1500:])
finally: h.close()
