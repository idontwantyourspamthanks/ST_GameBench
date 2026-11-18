from nl import *
h=boot()
try:
    print(h.debug('b pc = $3d6c4 :trace'))
    print(h.debug('b'))
    time.sleep(2)
    for i in range(6):
        out=h.debug('r',0.5)
        print(re.findall(r'PC[: ]+\s*([0-9a-fA-F]+)',out)[:1], out[:200].replace('\n','|'))
        time.sleep(0.3)
finally:
    h.close()
