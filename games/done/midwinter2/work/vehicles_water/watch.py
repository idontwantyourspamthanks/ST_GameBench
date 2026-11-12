import sys
from vw import *
def watch(snap, tag, live, pokes, cond, cmds, secs=60, extra_bps=()):
    h = Hatari(snapshot=str(snap), memsize_kb=2048)
    try:
        R = h.R
        hit = R / 'hit.txt'; hit.write_text("\n".join(cmds) + "\n")
        c = []
        if live: c += apply_cmds(live)
        c += list(pokes) + [f"b {cond} :trace :file {hit}"]
        for i, (cnd, cm) in enumerate(extra_bps):
            f2 = R / f'hit{i+2}.txt'; f2.write_text("\n".join(cm) + "\n")
            c.append(f"b {cnd} :trace :file {f2}")
        app = R / 'apply.txt'; app.write_text("\n".join(c) + "\n")
        v = h.vbl(); assert v < ABS_VBL - 20, v; start = len(h._logtext())
        h.cmd(f"hatari-debug b VBL > {ABS_VBL} && pc = $26e98 :trace :once :file {app}")
        time.sleep(secs)
        h.debug("b all", 0.5)
        txt = h._logtext()[start:]
        (OUT / 'logs' / f'{tag}.log').write_text(txt)
        return txt
    finally:
        h.close()
if __name__ == '__main__':
    live = live_build('t3', OUT/'patches', ['sw_head','sw_post','sw_ramp','sw_range','sw_probe2','p3b_pos','p3b_hdg','p3b_bank','p3b_alt','p3b_save','p3b_probe'])
    pokes = [wb(0x6fba,150<<16,4), wb(0x6fb6,(-160&0xffff)<<16,4), wb(0xb4e00,0x40,4)]
    txt = watch(SNAP/'raid_speedboat_iquitos.sav','watch1',live,pokes,'($6220).w ! ($6220).w',['r','m $6220 2','m $676e 2','m $b42e6 6'],secs=40)
    print(txt[:3000])
