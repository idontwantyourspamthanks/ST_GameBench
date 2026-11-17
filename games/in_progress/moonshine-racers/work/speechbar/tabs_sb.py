"""Tables from the stage_sb.py results (res/stage_final_<scene>_<set>.json): per class of the ticker state the cycles of the whole HUD stage and of its parts, the speech overhead (stage minus the
no-speech stage of the same set), and the saving of S / SF against F; plus the weighted saving over the scripted 1,707-pass race of hud.md (933 typing, 370 hold, 44 erase, 360 passes without speech).
python3 tabs_sb.py"""
import json, statistics as st
from pathlib import Path
R = Path(__file__).resolve().parent / 'res'
W = dict(typing=933, hold=370, erase=44, none=1707 - 933 - 370 - 44)
def cls(r):
    if r['b0'] != 0 or (r['s11ab_B'] != 0 and r['speech'] == 0): return 'erase'
    return 'none' if r['speech'] == 0 else ('typing' if r['speech'] == 1 else 'hold')
out = []
for scene in ('race_start', 'race_grid'):
    M = {}
    for v in ('F', 'S', 'SF'):
        f = R / f'stage_final_{scene}_{v}.json'
        if not f.exists(): continue
        rows = json.load(open(f))
        for c in ('none', 'typing', 'hold', 'erase'):
            sel = [r for r in rows if cls(r) == c]
            if sel: M[(v, c)] = dict(n=len(sel), stage=st.mean(r['stage'] for r in sel), ticker=st.mean(r['ticker'] for r in sel), face=st.mean(r['face'] for r in sel), topbar=st.mean(r['topbar'] for r in sel), hit=st.mean(r['hit'] for r in sel), mx=max(r['stage'] for r in sel))
    out.append(f'### {scene}: cycles of the HUD stage per pass (tick off, 8 MHz, interrupts included), by class of the ticker state')
    out.append('| class | n F/S/SF | stage F | stage S | stage SF | ticker F->S | face part F->S | overhead over "none" F / S / SF | saving S vs F | saving SF vs F |')
    out.append('|---|---|---:|---:|---:|---|---|---|---:|---:|')
    for c in ('none', 'typing', 'hold', 'erase'):
        g = lambda v, k: M.get((v, c), {}).get(k)
        if g('F', 'stage') is None: continue
        ov = lambda v: (g(v, 'stage') - M[(v, 'none')]['stage']) if g(v, 'stage') is not None and (v, 'none') in M else float('nan')
        out.append(f"| {c} | {g('F','n')}/{g('S','n')}/{g('SF','n')} | {g('F','stage'):.0f} | {g('S','stage'):.0f} | {(g('SF','stage') or float('nan')):.0f} | {g('F','ticker'):.0f} -> {g('S','ticker'):.0f} | {g('F','face'):.0f} -> {g('S','face'):.0f} | {ov('F'):.0f} / {ov('S'):.0f} / {ov('SF'):.0f} | {g('F','stage')-g('S','stage'):.0f} | {(g('F','stage')-(g('SF','stage') or float('nan'))):.0f} |")
    if all((v, c) in M for v in ('F', 'S') for c in W):
        tot = sum(W.values())
        for v in ('S', 'SF'):
            if all((v, c) in M for c in W):
                d = sum(W[c] * (M[('F', c)]['stage'] - M[(v, c)]['stage']) for c in W) / tot
                out.append(f'weighted over the scripted race (933/370/44/360 passes): {v} saves {d:.0f} cycles per pass = {d/160256:.4f} VBL on average vs F')
    out.append('')
print('\n'.join(out))
