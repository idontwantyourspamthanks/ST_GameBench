import re
from pathlib import Path
R = Path('/home/ryan/Code/AtariST/midwinter2/work/p7_skip')
note = Path('/home/ryan/Code/AtariST/midwinter2/work/notes/p7_static_skip.md')
def ev(n): return (R / 'evidence' / n).read_text().rstrip()
def strip(t):  # raw lines minus the constant 'npc0 x=0 y=0' tail where no unit is involved
    return t.replace(' npc0 x=0 y=0', '')
def boot(n):
    t = (R / 'boot' / f'{n}.log').read_text()
    keep = []
    for l in t.splitlines():
        if l.startswith(('cell', 'Wall time', 'Ran in a temporary')): continue
        keep.append(l)
    return '\n'.join(keep).rstrip()
g = []
g.append('Pixel gates compare the 32000 visible bytes of both buffers (`$60000`, `$70000`) after the stated flip counts, two Hatari instances, the same snapshot, the live set applied at the same flip (per-frame simulation, no tick/p3b/p5).\n'
         '"B counters" are the p7_skip counters at that flip (cumulative since the apply flip). Raw files: `work/p7_skip/evidence/`.\n')
g.append('### (a) standing, `1mb_ingame_foot`\n```\n' + strip(ev('a_base.txt')) + '\n\n' + strip(ev('a_unpatched.txt')) + '\n\n' + strip(ev('a_lobos.txt')) + '\n```\n')
g.append('### (b) walking, banked turn, turning (the skip must not fire)\n```\n' + strip(ev('b_walk.txt')) + '\n\n' + strip(ev('b_bank.txt')) + '\n\n' + strip(ev('b_turn.txt')) + '\n```\n'
         'Fire count: `NSKIP = 0` at every capture; every frame took the scalar-changed path (`NSC = NREND`).\n')
g.append('### stop-and-go (every transition into and out of a skipped state, with the whole default P7 set live)\n```\n' + strip(ev('stopgo.txt')) + '\n```\n'
         'and with only the clean-prefix set, or only the cull set, live, against the UNPATCHED game (tail of each):\n```\n' + '\n'.join(strip(ev('stopgo_pfxsk.txt')).splitlines()[-4:]) + '\n' + '\n'.join(strip(ev('stopgo_cksk.txt')).splitlines()[-4:]) + '\n```\n')
g.append('### (c) something moves while the player stands (unit poked into the NPC table, `$2e = 1`, state 0; its own AI moves it)\n'
         'Near unit, 2224 units ahead (inside the window, visible as a small figure), moving; the skip must not freeze it:\n```\n' + ev('c_npc_near.txt') + '\n```\n'
         'Screenshots (`gate.py --png`, buffer `$60000` of A = base and B = base + skip at the captured flips): `/tmp/sk/g/npc1/{A,B}_{6..40}_60000.png`; the figure moves between flips in both and the two are identical (0 differing bytes above).\n\n'
         'Unit active but 17400 units away (outside the 16-cell window, AI idle there: `npc0` does not move) and then a far unit repositioned by poke at flips 10/14/18/22 (always > 13000 units away); the skip keeps firing, the picture is identical:\n```\n' + ev('c_npc_far.txt') + '\n\n' + ev('c_npc_far_moving.txt') + '\n```\n'
         'Unit movement radius (`npcrad.py`: six units poked at 2000..12000 units, positions 4 s apart):\n```\n' + ev('npc_radius.txt') + '\n```\n'
         'Sea in view (player 8 cells east, heading east; the sea cells use the wave table): the picture is identical, `WV = (1,1)`, `NSKIP = 0`, `NWAV` rises: the animated sea is never skipped:\n```\n' + ev('c_sea.txt') + '\n```\n'
         'Other writers of the window: the render gate `$6298` (on at flip 10, off at 14) and a HUD message (`$7590 = 5`, text drawn into the window after the render):\n```\n' + ev('gate6298.txt') + '\n\n' + ev('msg.txt') + '\n```\n')
g.append('### (d) cold boot of the full default build + p7_skip (`build/p7skip`, `work/p7_skip/boot_skip.py`)\n'
         'Same session, skip live vs the `p7_skip_render` site restored to its original bytes (`$1dbbe: 203866e604800000 6400`), `h.fps(1000)` = flips per 1000 VBL; the other six hooks stay applied. Walking is a short walk (the cliff 6000 units west of the start turns the player into another type).\n'
         '**1 MB STE, TOS 1.62** (`boot/ste1mb.log`):\n```\n' + boot('ste1mb') + '\n```\n'
         '**4 MB Mega STE, TOS 2.06** (`boot/mste4mb.log`):\n```\n' + boot('mste4mb') + '\n```\n'
         'Screenshots: `work/p7_skip/boot/{ste1mb,mste4mb}_{stand,walk,turn,stand2,npc0,npc1,npc2}.png`.\n')
txt = note.read_text()
txt = txt.replace('GATES_PLACEHOLDER', '\n'.join(g))
note.write_text(txt)
