from ui import *
import shutil, sys
gd=__import__('pathlib').Path
part=sys.argv[1]
if part=='A':       # absent NEBLEVEL.OVL on the disk: Save fails cleanly; then F9 in the editor
    os.system(f"cd {G} && python3 tools/nepatch.py build --out work/editor/build_noovl --only nt_trainers ed_overlay >/dev/null; rm -f work/editor/build_noovl/NEBLEVEL.OVL")
    h=start('/tmp/ned120A',gd(E+'build_noovl'))
    try:
        h.key('F10',hold=0.5); time.sleep(2)
        select(h,'Save to disk',1.0); time.sleep(3); h.shot(E+'e120_savefail.png')
        print('vErr',hex(L(h,0x77cf4)),'(GEMDOS error code: -33 = file not found)',flush=True)
        v0=h.vbl(); K(h,'Down'); print('alive: vbl',v0,h.vbl(),'menu sel',menu(h)[1],flush=True)
        h.key('F9',hold=0.5); time.sleep(6); h.shot(E+'e120_f9.png'); print('after F9: vbl',h.vbl(),flush=True)
    finally: h.close()
else:               # B: store overwritten by garbage while a campaign runs (what an F9 restore does to $BC000)
    os.system(f"cd {G} && python3 tools/nepatch.py build --out work/editor/build_final --only nt_trainers ed_overlay --ovl /tmp/test3.ovl >/dev/null")
    h=start('/tmp/ned120B',gd(E+'build_final'))
    try:
        h.key('F10',hold=0.5); time.sleep(2)
        select(h,'Campaigns'); select_i(h,0); select(h,'Play',0.5)
        time.sleep(7); K(h,'e',hold=0.3,gap=0.5)
        print('before',rs(h)[:3])
        open('/tmp/garb.bin','wb').write(bytes((i*37+11)&255 for i in range(8192)))
        h.debug('loadbin /tmp/garb.bin $bc000',0.8)
        poke(h,0x33a46,bytes([0,1])); poke(h,0x33a20,bytes([0,4])); poke(h,0x33a1e,bytes([0,0]))
        t0=time.time()
        while time.time()-t0<80 and W(h,0x3390c)!=8: time.sleep(1.5)
        time.sleep(4); print('after garbage + completion: rs',rs(h)[:3],'tower',W(h,0x3390c),'vbl',h.vbl(),h.vbl(),flush=True)
        h.shot(E+'e120_garbage.png')
        log=open('/tmp/ned120B/log.txt',errors='replace').read(); print('error lines:',len([l for l in log.splitlines() if 'Address Error' in l or 'Illegal' in l]))
    finally: h.close()
