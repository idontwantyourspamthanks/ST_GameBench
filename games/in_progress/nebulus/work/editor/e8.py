from ed import *
h=snap('/tmp/ned8')
try:
    time.sleep(3)
    print(h.debug('m $fffa01 48',0.8))
    print(h.debug('m $fff80 32',0.6))
    print(h.debug('m $fffaa 32',0.6))
    print(h.debug('m $ffd7e 12',0.6))
    a=W(h,0x4ba); time.sleep(2); b=W(h,0x4ba); print('hz200',a,b)
    print(h.debug('m $ffe4a 16',0.6))
finally: h.close()
