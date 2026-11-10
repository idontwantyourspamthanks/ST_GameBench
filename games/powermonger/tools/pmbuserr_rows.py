"""PMBusErr: histogram of the row counts (d2) of the sprite blit calls (p4_spr entry $bd500) over 700 VBL of a snapshot, with the p4 + p6_cpy set live.

    python3 tools/pmbuserr_rows.py get_men [battle_320 ...]

get_men: calls 37, max rows 24 [(1, 1), (2, 2), (24, 34)] (work/notes/buserr.md section 6).
"""
import sys,time,re,collections,shutil
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/powermonger/tools')
from pmab import *
T=TICK+['p4_ptr_a','p4_ptr_b','p4_spr','p6_cpy']
live=make_live(T)
for snapn in sys.argv[1:]:
    sp=snap_path(snapn); at=at_vbl_for(sp)
    shutil.rmtree('/tmp/pmbe/h1',ignore_errors=True)
    h=make_pm(snapshot=str(sp),memsize_kb=1024,workdir='/tmp/pmbe/h1')
    try:
        R=h.R; time.sleep(1)
        cmds=apply_cmds(live)
        (R/'d2.txt').write_text("e d2 & $ffff\n")
        cmds.append(f"b pc = $bd500 :trace :file {R/'d2.txt'}")
        (R/'end.txt').write_text(f"b all\nsavebin {R}/end.flag $0 2\n")
        cmds.append(f"b VBL > {at+700} :trace :once :file {R/'end.txt'}")
        (R/'apply.txt').write_text("\n".join(cmds)+"\n")
        start=len(h._logtext())
        h.cmd(f"hatari-debug b VBL > {at} && pc = $1880 :trace :once :file {R/'apply.txt'}")
        time.sleep(0.3); h.cmd("hatari-option --fast-forward on")
        t=time.time()
        while not (R/'end.flag').exists() and time.time()-t<300: time.sleep(0.5)
        txt=h._logtext()[start:]
        vals=[int(m) for m in re.findall(r"#(\d+) \(dec\)",txt)]
        c=collections.Counter(vals)
        print(snapn,'calls',len(vals),'max rows',max(vals) if vals else None,sorted(c.items()))
    finally: h.close()
