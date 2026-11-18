import subprocess, json, re, statistics as st, collections, os
G = '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers'
os.chdir(G + '/work/tint')
def sh(c):
    return subprocess.run(c, shell=True, capture_output=True, text=True, cwd=G + '/work/tint').stdout.rstrip()
def cmpst(a, b, extra='--mask --nogeomask', n=40):
    return '\n'.join(sh(f'python3 cmpstate_int.py res/st_{a}.json res/st_{b}.json {extra}').splitlines()[:n])
out = []
P = out.append
P("## 11. Tightening integration (MSRTightIntegrate): the ta_*/tc_*/tb_car patches as defaults, gates, measured result")
P("Machine: Hatari 2.6.1, headless harness (cycle-exact, `--fast-boot yes`), STE TOS 1.62 1 MB unless named. Scripts: `work/tint/` (`mxlib_int.py` builds every variant with the REAL `tools/msrpatch.py live` from its own default selection, so the gates test exactly what `build` ships; `exp_state_int.py`, `cmpstate_int.py`, `pix_int.py`, `steer_int.py`, `cyc` via `steer_int.py mode=cyc`, `cold_int.py`, `play5_int.py`, `ext_summary.py`, `cmp_cyc.py`, queues `run_q6.sh run_q7.sh run_q8.sh`); raw outputs `work/tint/res/`. `[INFERENCE]` marks what no output here proves. Nothing here touches `originals/`.")
P("")
P("### 11.1 The default set, `list`, `verify`, sizes, the RAM map")
P("Defaults flipped (`; default: yes` in the patch headers): `ta_erase ta_init ta_face ta_glyph ta_ymw`, `tc_clr tc_proj tc_dist tc_hit1 tc_hit2 tc_ord`, `tb_car tb_carph`; `hd_init` is now `default: no` (`ta_init` replaces it: declared `conflicts: hd_init` in `ta_init.s`; the tool refuses both together). Not default (documented as options): `ta_rb ta_rb0` (raster timing unproven on real hardware), `ta_nomouse` (behaviour risk, needs the user's approval), `ta_facestat` (visible), `tc_clrx`, `tb_blit tb_blit11 tb_blit13 tb_blit15` (not worth it), `hd_init`; `mx_*` stay default.")
P("```")
P(sh("cd %s && python3 tools/msrpatch.py verify 2>&1 | tail -1; python3 tools/msrpatch.py list | grep -E ' yes ' | cut -c1-120; python3 tools/msrpatch.py list | grep -E 'valid layouts|ta_init|hd_init |tb_car |tc_clr '; python3 tools/msrpatch.py build --out build/tight_hd 2>&1 | grep -E '^built'; python3 tools/msrpatch.py build --floppy --out build/tight_floppy 2>&1 | grep -E '^floppy:'" % G))
P("```")
P("Payload 47,360 B (HUD build) -> **54,568 B** (`$B2700-$BFC27`, 107 floppy sectors). RAM map at 1 MB (and 4 MB, TOS 2.06 1 MB ceiling `$E2BFF`): `$B6800-$B6FFF` tc_*, `$BE000-$BEFFF` ta_*, `$BF000-$BFFFF` tb_car/tb_carph, `$C0000-$CAFFF` rd_geom RAM, `$CB000-$D7FFF` rd_draw RAM, **`$D8000-$E2BFF` tb_car code cache = 44,032 B (0xAC00; the task text said 43,008 B, which is a miscount of the same range: `$E2C00 - $D8000 = $AC00`)**. `verify` ALL OK includes the whole-free-run zero check against the six STE 1.62 dumps and the three Mega STE 2.06 1 MB dumps and `; ram:` zero in all of them; `POOLEND` in `tb_car.s` is `$E2C00`. 4 MB layout: same addresses (`pp_bigram_cache` default).")

# ---------------- 11.2 per-pass state
P("")
P("### 11.2 Per-pass game state equal to stock (Hatari, `$7b86` after the flip, keyed by `$100e`; `m` counts DECIMAL: `$1000-$13ff` (1024) `$29c8` (2872) `$4500` (2816) `$dae6` (4) `$1bb0` (12) `$23bc` (16) `$27c8` (38) `$3500` (512) `$dafe` (4) `$6100` (24) `$b8f38` (12) = 7,334 bytes per pass)")
P("A = stock game, T = the real default set with `mt_sync` (tick ON, no extras), X = the real default set (tick ON + extras). Stock vs T, race_start (driving, 220 passes asked) and race_drive (300 asked; the time-out and the restart are inside: keys 0..1706), mask = the documented HUD-private/display-scratch list, **`TC_GEOM` (road geometry output `$4724-$4f77`) NOT applied (`--nogeomask`)**:")
P("```")
P(cmpst('start_A8', 'start_T8', n=14)); P(""); P(cmpst('drive_A8', 'drive_T8', n=16))
P("```")
P("Final mask set (all in `cmpstate_int.py`, each a named range with a per-category count of masked differing bytes printed): IKBD mouse reply bytes `$6106-$6117` (written by the ACIA interrupt, asynchronous to the pass: ONE byte differed once in race_drive pass key 0 without the mask: `$0610e 00 -> 03`; this range is new in this gate and was not in the earlier HUD gate), buffer parity/pointer `$1004-$100d`, raster scratch `$12f0-$1307`, raster bands `$12fe-$1301`, object order list scratch `$36e8-$36ff`, HUD kernel scratch `$100c-$100d`, the HUD caches/flags the removed old HUD items used to update (`$10bc-$10bd $11c9`, `$10c2-$10c9`, `$10cc-$10cd $11cc`, `$10d4-$10d7 $11cd`, `$10dc-$10e3`, `$11c4-$11c5 $11c7`, `$11ca-$11cb`, `$11da-$11dc`) and the cloud slots/counters `$29c8-$2c67`, `$27de-$27ed` (`dd50` removed with the clouds). **`TC_GEOM` is not needed with `tc_clr`** (the 'start'/'drive' blocks above); it is still needed in the extras gates, because an extra frame re-runs the road geometry at an extrapolated pose and the region holds the last extra's output at `$7b86` (below).")
P("")
P("Extras at 16 and 32 MHz, same keys (`X` vs stock, mask + `TC_GEOM` as documented for the extras gates; the unmasked-by-TC_GEOM counts are printed to show that the ONLY other difference is that region):")
P("```")
for a, b in (('start_A8', 'start_X16'), ('start_A8', 'start_X32'), ('drive_A8', 'drive_X16')):
    P("-- %s vs %s: with TC_GEOM:" % (a, b)); P(cmpst(a, b, '--mask', 3)); P("-- without TC_GEOM:"); P(cmpst(a, b, '--mask --nogeomask', 2))
P("```")
for f in ('start_X16', 'start_X32', 'drive_X16'):
    pass
P("Extras counts in those windows (`$b8f38` over the recorded passes, from `res/state_log.txt`): " + sh("grep 'extra frames' res/state_log.txt | grep -E '^X' | sed 's/bytes\\/hit 7334 //' | tr '\\n' ';'") + " The race_drive scene itself draws **0** extras at 16 MHz in those 300 passes (time-out and the standing start dominate: skip reasons, 11.6), so the steered gates below are the strong extras gate.")
P("")
P("Steered state gates (input = a pure function of the pass key `$100e`, identical in every run: from key 140 (race_start) / 470 (race_up) 15 passes each of up, up+left, up, up+right; the player car changes bitmap constantly, so `tb_car` generates and uses code), mask as above, `TC_GEOM` only for X:")
P("```")
for a, b, ex in (('zig_start_A8', 'zig_start_T8', '--mask --nogeomask'), ('zig_up_A8', 'zig_up_T8', '--mask --nogeomask'), ('zig_start_A8', 'zig_start_X16', '--mask'), ('zig_start_A8', 'zig_start_X32', '--mask'), ('zig_up_A8', 'zig_up_X16', '--mask')):
    if os.path.exists('res/st_%s.json' % b): P("-- %s vs %s (%s):" % (a, b, ex)); P(cmpst(a, b, ex, 2))
    else: P("-- %s vs %s: NOT RUN" % (a, b))
P(sh("grep -E 'hits|extra frames' res/state_log4.txt | sed 's/bytes\\/hit 7334 //'"))
P("```")
# ---------------- 11.3 pixels
P("")
P("### 11.3 Pixels")
P("**(a) Full-buffer A/B** (`pix_int.py`: R = the HUD-build default `mr_edge rd_* hd_stage hd_init hd_clouds hd_nomap hd_nomap2`, C = the default set minus the pacer, both live-applied at the same instant, both 32,000-byte buffers, 7 render controls on the SAME capture; flips after the apply as listed; `$11ab` = ticker state). Summary over the captures, then the raw lines of the message-active captures:")
t = open('res/pix_ctl.txt').read(); caps = t.split('== ')[1:]
ci = 0; fire = collections.Counter(); msgc = 0
for c in caps:
    hdr = c.splitlines()[0]; act = int(re.search(r'\$11ab=(\d+)', hdr).group(1)) != 0; msgc += act
    for ln in c.splitlines()[1:]:
        nm = ln.split()[0]; ok = 'IDENTICAL' in ln
        if nm == 'C': ci += ok
        elif not ok: fire[nm] += 1
P("`%d` captures (race_start flips 10 55 90 100 150, race_grid 10 120 150, race_up 10 40 90 150, race_drive 10 40 90 150): **C identical to R in %d/%d** (both buffers). Ticker message active (`$11ab != 0`): %d captures. Negative controls (C + one poke), captures in which each control DIFFERS: %s." % (len(caps), ci, len(caps), msgc, ', '.join('%s %d' % (k, v) for k, v in sorted(fire.items()))))
P("```")
for c in caps:
    hdr = c.splitlines()[0]
    if int(re.search(r'\$11ab=(\d+)', hdr).group(1)) != 0 or 'flip 90' in hdr:
        P('== ' + c.rstrip())
P("```")
P("The controls: `face_same` (ta_face always 'same': `be112=600e`), `face_wrong` (draws sprite+1: `be11a=b0e4`), `erase_short` (`be042=0040`), `glyph_bad` (`be660=0002`), `car_nophase` (the `tb_carph` hook removed: `ed90=302a0006d06a0008`, i.e. the wheel-animation state is not tracked: the bank alternates and a stale compiled frame is drawn). `car_nophase` fires in %d capture(s) only (the XOR toggles every other pass; the earlier tighten-B gate also saw it in a single capture); the three face/erase/glyph controls fire exactly where a message is on screen." % fire.get('car_nophase', 0))
P("")
P("**(b) Masked gate against the real stock/HUD reference** (`tools/msrmask.py`, explicit rectangles, pixels compared AND excluded printed): cand = the default set, ref = `test_hdref hd_clouds mr_edge rd_*`, stock side = `mr_edge rd_*`, 4 scenes x flips 10 40 90 x both buffers = 24 frames (message active on several: `speech=Y` rows):")
P("```")
P(sh("grep -E 'speech=Y' res/mask_final.txt | head -6 | cut -c1-140; tail -6 res/mask_final.txt | cut -c1-175"))
P("```")
P("Negative controls (`--neg nopaint`: the first strip/sky paint is skipped, `--neg nowipe`: the sky wipe is skipped; each MUST differ):")
P("```")
P(sh("for f in res/mask_neg_nopaint.txt res/mask_neg_nowipe.txt; do echo \"-- $f\"; tail -6 $f | cut -c1-175; done"))
P("```")

# ---------------- 11.4 cycles
CYC = 160256
def LD(f):
    d = json.load(open(f)); return d['rows'] if isinstance(d, dict) else d
def means(f):
    r = LD(f); o = {}
    for nm, sp in (('ns', False), ('sp', True)):
        w = [x['work'] for x in r if x['speech'] == sp]; o[nm] = (len(w), round(st.mean(w)) if w else None)
    return o
def matched(a, b):
    A = {x['p']: x for x in LD(a)}; B = {x['p']: x for x in LD(b)}; o = {}
    for nm, sp in (('ns', False), ('sp', True)):
        ks = [k for k in A if k in B and A[k]['speech'] == sp and B[k]['speech'] == sp]
        o[nm] = (len(ks), round(st.mean(A[k]['work'] for k in ks)), round(st.mean(B[k]['work'] for k in ks))) if ks else None
    ks = sorted(set(A) & set(B)); o['all'] = (len(ks), round(st.mean(A[k]['work'] for k in ks)), round(st.mean(B[k]['work'] for k in ks)))
    return o
P("")
P("### 11.5 MEASURE: cycles per pass at 8 MHz, tick OFF (loop top `$796a` -> flip `$d1ca`, interrupts included; 1 VBL = 160,256 cycles; same Hatari session and recipe as `work/hud/build/res_cyc3.txt`)")
P("Rows: N = the HUD-build default (`mr_edge rd_* hd_stage hd_init hd_clouds hd_nomap hd_nomap2`, re-measured now: the baseline), F = the new default minus the pacer (the cycle recipe needs the tick off). `speech` = `$11ab != 0` at the end of the pass (as in the earlier tables); both rows are matched on the same pass key `$100e` (same snapshot, same instant), so `delta` compares the same passes. race_start = driving (up held, no steering), race_grid = standing.")
P("```")
P("%-11s %-10s %5s  %9s %7s  %9s %7s  %9s %8s" % ('scene', 'passes', 'n', 'N cycles', 'VBL', 'F cycles', 'VBL', 'delta', 'VBL'))
for sc in ('race_start', 'race_grid'):
    m = matched('res/cyc_%s_N.json' % sc, 'res/cyc_%s_F.json' % sc)
    for nm, lab in (('ns', 'no speech'), ('sp', 'speech'), ('all', 'all')):
        n, a, b = m[nm]
        P("%-11s %-10s %5d  %9d %7.3f  %9d %7.3f  %9d %+8.3f" % (sc, lab, n, a, a / CYC, b, b / CYC, b - a, (b - a) / CYC))
P("```")
P("Unmatched window means (all passes of each 230-pass run, `res/cyc_log.txt`): " + sh("grep -E 'speech|all passes|VBL per pass' res/cyc_log.txt | tr '\\n' '|' | sed 's/|/ | /g'"))
P("")
P("Per-agent savings overlap (shared stages): the sum of the three agents' stand-alone claims (A 7-20 k, B 39-42 k, C 7.3-9.2 k) is 53-71 k; the integrated, matched result is **-46.7 k / -53.5 k driving (no speech / speech) and -52.4 k / -55.3 k standing**.")
P("")
P("**Steering and the pool (key-matched, 8 MHz, tick OFF, race_start, input = zig = up / up+left / up / up+right, 15 passes each from key 140; 520 passes; `steer_int.py mode=cyc zigk=140`).** N = HUD build, nocar = the default set minus `tb_car tb_carph`, pK = the default set with the `tb_car` pool limit poked (`cmpi.l #POOLEND,d0` immediate at `$BF772`) to `$D8000 + K KB`; compiled-draw fraction = executions of the generated-code hit path `$BF5E6` / executions of the stub `$BF500` (the stub is entered by every 4-column nibble-7 sprite, the car, its second layer and other objects; 'hits' also counts the draw right after a generation), counted by trace breakpoints in the same run:")
P("```")
P("%-22s %9s %7s  %11s %9s  %s" % ('variant', 'mean cyc', 'VBL', 'vs nocar', 'vs N', 'compiled-draw fraction (hits / stub entries)'))
def mean_all(f): 
    r = LD(f); return round(st.mean(x['work'] for x in r))
base = {k: mean_all('res/pool_%s.json' % k) for k in ('N', 'nocar')}
for k in ('N', 'nocar', 'p8', 'p16', 'p24', 'p32', 'p44'):
    f = 'res/pool_%s.json' % k
    if not os.path.exists(f): continue
    m = matched('res/pool_nocar.json', f)['all']; mn = matched('res/pool_N.json', f)['all']
    d = json.load(open(f)); e = sum(1 for kk, _ in d.get('cars', []) if kk == 'entry'); h = sum(1 for kk, _ in d.get('cars', []) if kk == 'hit')
    frac = ('%d / %d = %.1f %%' % (h, e, 100 * h / e)) if e else '-'
    tail = d.get('tail', {}).get('0xbf000', '')
    P("%-22s %9d %7.3f  %+11d %+9d  %s%s" % ({'N': 'N (HUD build)', 'nocar': 'default w/o tb_car'}.get(k, 'default, pool ' + k[1:] + ' KB'), m[2] if k != 'N' else mn[1], (m[2] if k != 'N' else mn[1]) / CYC, (m[2] - m[1]) if k not in ('N',) else 0, (mn[2] - mn[1]) if k != 'N' else 0, frac, ('   (pool used up to $%s, %d entries)' % (tail.replace(' ', '')[8:14].lstrip('0') or '0', int(tail.replace(' ', '')[16:20], 16))) if tail else ''))
P("```")
P("(`vs nocar` / `vs N`: mean over the matched passes of the 520-pass window, i.e. including the cold generation of every variant in the first ~100 passes; steady state from key +250 is 1-2 k better, see `res/pool_log.txt`.) The entry table (39 entries) never binds at 44 KB: 29 entries are used; an experimental 120-entry table (Unicorn census, `work/tightB/census.py`, not kept) changed the compiled fraction by -1..-2 points only, so the table was not enlarged. **Raising the pool from 24 KB to 44,032 B lifts the compiled-draw fraction from 55.1 % to 78.2 % under constant steering and saves a further 10.3 k cycles per pass (-0.064 VBL); against the 24 KB version's 47-68 % Unicorn estimate the Hatari measurement is 55 % at 24 KB** (the estimate was a model, this is the live count).")

# ---------------- 11.6 extras per tick
def racing(f):
    R = json.load(open(f))['rows']
    i0 = next((i for i, (a, b) in enumerate(zip(R, R[1:])) if b['p'] + 20 < a['p']), -1) + 1
    j = next((i for i in range(i0, len(R)) if R[i]['p'] >= 130), 0)
    seg = R[j:]; dv = seg[-1]['vbl'] - seg[0]['vbl']; n = len(seg) - 1; fr = seg[-1]['frames'] - seg[0]['frames']
    per = [b['nextra'] for a, b in zip(seg, seg[1:])]; h = collections.Counter(per)
    sp = [b['nextra'] for a, b in zip(seg, seg[1:]) if b['speech']]; ns = [b['nextra'] for a, b in zip(seg, seg[1:]) if not b['speech']]
    return dict(n=n, dv=dv, fr=fr, h=h, mean=sum(per) / n, sp=(sum(sp) / max(len(sp), 1), len(sp)), ns=(sum(ns) / max(len(ns), 1), len(ns)), fps=(n + fr) / dv * 50, pps=n / dv * 50)
P("")
P("### 11.6 MEASURE: extra frames per tick (mx counters), tick ON (T=30), extras ON, STE, driving with steering")
P("`steer_int.py mode=pass`: a persistent trace breakpoint at the race-pass top `$7a88` dumps, per pass, `NEXTRA $b8f32` (the extras drawn in the PREVIOUS pass's tick), the pass key, the counters `$b8f38/3c/40` (frames / ticks with >= 1 extra / ticks that entered the group code), the skip-reason words `$b8f54`, `$11ab`, `$1226`, `$1021`, the VBL; input = zig steering as a pure function of the key (up / up+left / up / up+right, 15 passes each, also after the restart). Scene race_drive: ~65 passes of the time-out sequence (`$1226 = 5`), the race restart (pass 1707 -> 0), 94 standing passes of the start sequence (skip reason 2 = standing), then racing. 1,300 passes = 6,500 VBL = 130 s emulated per run. Per-run raw: `res/ext_*.json`, summary `ext_summary.py`.")
P("**Frames per tick = 1 main + extras. Racing phase only (after the restart, pass >= 130; the first lap of the new race):**")
P("```")
P("%-26s %6s %8s %7s  %-44s %9s %7s %8s" % ('run', 'ticks', 'VBL/tick', 'pass/s', 'extras per tick histogram {extras: ticks}', 'mean ex.', '2-frame', 'disp fps'))
for k, lab in (('NX_8', 'HUD build (NX) 8 MHz'), ('X_8', 'NEW default 8 MHz'), ('X_16', 'NEW default 16 MHz'), ('X_32', 'NEW default 32 MHz')):
    f = 'res/ext_%s.json' % k
    if not os.path.exists(f): continue
    r = racing(f)
    P("%-26s %6d %8.3f %7.3f  %-44s %9.3f %6.1f%% %8.2f" % (lab, r['n'], r['dv'] / r['n'], r['pps'], str(dict(sorted(r['h'].items()))), r['mean'], 100 * r['h'].get(1, 0) / r['n'], r['fps']))
P("```")
P("`2-frame` = share of ticks with exactly one extra (main + 1 = 2 pictures); `disp fps` = (passes + extras) per second of the racing window (the game itself runs 10 logic steps per second in every row). With the tick ON the passes stay at 10.00/s in all rows, so the game speed is not affected by the extras.")
P("Full-window view incl. the time-out sequence, the restart and the 94 standing passes (`ext_summary.py`; this is what an observer sees over 2 minutes):")
P("```")
P(sh("python3 ext_summary.py res/ext_X_8.json res/ext_X_16.json res/ext_X_32.json res/ext_NX_8.json | cut -c1-330"))
P("```")
for k in ('X_8', 'X_16', 'X_32'):
    r = racing('res/ext_%s.json' % k)
    P("- %s: ticker active (`$11ab != 0`, %d ticks) mean %.3f extras, ticker idle (%d ticks) %.3f." % (k, r['sp'][1], r['sp'][0], r['ns'][1], r['ns'][0]))
P("Other scenes at 8 MHz (steered, 700 passes, `res/ext8_*.json`; the amount of spare time depends on the scene: objects, speech):")
P("```")
P(sh("for sc in race_start race_up; do for v in NX X; do f=res/ext8_${sc}_$v.json; [ -f $f ] && python3 ext_summary.py $f | sed -n '1,4p' | cut -c1-300; done; done"))
P("```")
P("Time-out restart: no extras during the time-out sequence (skip reason 5 / `$1024 != 0`) and none in the standing start sequence (skip reason 2 = standing, 94 passes), both unchanged by the tightening; the extras resume when the car moves. In the full-window summaries above the lines `restart at record ...` show the extras of the 20 passes around the restart: all 0.")
P("")
P("**Reading for the STE at 8 MHz [measured above, the interpretation is an INFERENCE]:** after the tightening the pass costs ~2.8-2.9 VBL of a 5-VBL tick, but an extra frame needs the whole road/object path again (about the same cost minus the logic stage and the HUD work), so only part of the ticks have room for one: the new default draws one extra picture in about 29 % of the racing ticks (the HUD-build default: 15 %), ~12.9 displayed fps instead of 11.5; it can never draw two. The deadline rule (`wantnext`) only starts an extra when it is predicted to flip before the next tick; 79 of the 349 extra-drawing ticks in the 137-s window still ended one or two VBL late (the next tick is then shortened: passes per second stay 10.00), see the VBL histogram: `VBL between pass starts: 3 x3, 4 x77, 5 x1153, 6 x76, 7 x3` (`res/ext_X_8.json`).")

# ---------------- 11.7 cold boots etc.
P("")
P("### 11.7 Cold boots, floppy, 5-minute plays, native 60 Hz")
P("HD: `work/tint/cold_int.py` (cold boot of `build/tight_hd` = the default HD build, SPACE navigation into the first race, marker `$b2700`, patched sites, HUD strip pixels == shadow render in both buffers, road tables `RDG1`/`WPTR`, `tb_car` probe byte `INIT $bf000` (1 = generated path on, 2 = stock kernel), `tc_clr` flag `$b6ff0`, then rate windows at the native clock and at 16 MHz (68000 machines boot at 8 MHz and the clock is raised after the boot, as `play.sh --cpu 16` does), `up` held, then 124 s of play; `$ff820a` read for the refresh rate). Raw `res/cold_hd.txt`:")
P("```")
P(sh("grep -E '^===|boot_to_race|^marker|^TB_CAR|^RESULT|PLAY DONE|STRIP CHECK' res/cold_hd.txt | sed -E 's/message\\/face excluded\\? no: raw/raw/' | cut -c1-330"))
P("```")
P("All eight machines boot to the race with marker `MSPO`, the new sites patched (`$17c24 -> $b6d40`, `$e406 -> $b6820`, `$39ac -> $bf500`), road tables intact, `$1021 = 2` after 124 s of play, and 0 Bus/Address Error lines on Mega STE/TT/Falcon (2-3 on ST/STE are PP's `$ff8e21`/`$ff8924` probes, as in the stock game, `integration.md` 10.6). **`tb_car` probe: `INIT = 1` (generated path ON) on STE 1.62 1 MB/4 MB and ST 1.04; `INIT = 2` (stock kernel) on Mega STE 2.06 (1/2/4 MB), TT 3.06 and Falcon 4.04, exactly the declared rule.** STRIP CHECK lines (the HUD pixel/shadow check) are identical to the HUD-build default's (`mste/m_hd.txt`: e.g. `non-sky pixels rows 16-64 2743` / `1750`/`1793`, the 'shadow==model False' flag at pass 397 appears in the HUD-build run as well, a timing artefact of the check) = the render with all patches equals the earlier default's. At the native 8 MHz clock the STE windows show 0 extras (the first lap right after the start light: ticker message active, objects, start sequence: no room), the 16 MHz windows 173-174 extras in 105 passes (26.5 fps); the 60 Hz boots (Mega STE 2.06 `$ff820a = fc`, TT 3.06 `$ff820a = 01`) run 10.000 passes per second at 60 Hz; the Mega STE draws 112-116 extras in 105 passes, the TT 526 (60 fps displayed).")
P("")
P("Floppy (`tools/msrfloppy.py gate build/tight_floppy/disk_a.st --disk-b build/tight_floppy/disk_b.st`, disk A alone, story screens, disk-2 swap, race, clock raised to 16 MHz, `up` held; raw `res/cold_floppy.txt`):")
P("```")
P(sh("grep -E '^=== FLOPPY|disk-2 prompt|^after swap|^marker|^road magic|^extra-frame' res/cold_floppy.txt | cut -c1-230"))
P("```")
P("")
P("5-minute plays, default HD build, STE 1.62 1 MB (`work/tint/play5_int.py`: cold boot, SPACE, `up` held plus a wall-clock left/right toggle every 6 s, 16,700 VBL = 334 s, samples every 10 s, a screenshot 6 s after each restart; the 8 MHz run is the native clock, the 16 MHz run switches the clock after the boot). Raw `res/play5_8.txt`, `res/play5_16.txt`; screenshots `work/tint/shots/play5_ste_1024_{8,16}_after_restart1.png` (HUD strip, message and face, road, car and objects intact after the restart: viewed):")
P("```")
for f in ('play5_8', 'play5_16'):
    P("-- " + f)
    P(sh("grep -E 'in_race|RESTART|shot after|^extras|^marker|^alive|^road' res/%s.txt | cut -c1-260" % f))
    P(sh("grep -E '^\\(' res/%s.txt | awk 'NR%%6==1' | cut -c1-120" % f))
P("```")

P("")
P("### 11.8 Not done / unproven / for the user")
P("- **Steered state gates (zig) and the other-scene 8 MHz extras runs (race_start/race_up) were NOT completed** (queued `run_q7.sh`, `run_q8.sh`, stopped for time; the rows above say NOT RUN). The state evidence for `tb_car` with a constantly changing bitmap is therefore: the tighten-B gates (8/8, incl. extras at 8/16/32 MHz and race_drive restart), the pixel gate here (16/16 identical, steering input in the race_up/race_drive snapshots is the snapshot's), and the 5-minute plays (steered by wall clock, 1 restart, no crash); NOT a per-pass state gate under steering on the integrated build. Re-run: `work/tint/run_q7.sh` (waits for `res/all.done`: `touch` it).")
P("- race_drive extras gate at 16 MHz saw 0 completed extras (time-out/standing dominate); the extras state gate is carried by race_start X16/X32 (334 / 888 extras).")
P("- Hatari only; no real hardware; the Mega STE cache is not emulated (tb_car is off there by rule). `ta_rb*`, `ta_nomouse`, `ta_facestat`, `tc_clrx`, `tb_blit*` stay options.")
P("- The 8 MHz extras statement 'draws none' in older notes is superseded: measured 15 % of ticks (HUD build) and 29 % (new default) in the race_drive scene; 0 in the first lap right after the start light (cold windows).")
P("- Decision for the user: none blocking. Optional: ta_nomouse (-8.3 k/pass), ta_rb/rb0 (-4.5 k) would take driving to about 2.7 VBL.")
print('\n'.join(out))
