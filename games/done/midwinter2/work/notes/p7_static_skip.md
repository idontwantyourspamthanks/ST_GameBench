# P7 item 5(a): static-frame skip (`patches/p7_skip_*`)

All seven patches are `default: no`. Evidence tooling and raw logs: `work/p7_skip/` (`rdset.py`, `chanN.py`, `cover.py`, `scrscan.py`, `gate.py`, `run_gates.sh`,
`boot_skip.py`, `evidence/*.txt`, `boot/*.log`). Unobserved statements are marked `[INFERENCE]`.

## 0. Result

| | |
|---|---|
| Standing, per-frame simulation (`1mb_ingame_foot`, p4+p7 set, 20 frames, `Hatari profile`) | **1,598,307 → 287,881 cy/frame (-82.0 %)**; the hook itself is 13,751 cy/frame (4.8 % of what is left) |
| Standing, cold boot, full default build, flips per 1000 VBL | 1 MB STE: **95 → 501** (4.75 → 25.05 fps); 4 MB Mega STE (TOS 2.06): **130 → 496** (6.5 → 24.8 fps). 25 fps is the p3b sub-tick limit (2 VBL) |
| Pixel identity (visible 32000 B per buffer) | standing 10/40/100 flips vs p4+p7 and vs UNPATCHED; walking, banked turn, turning; stop-and-go; moving NPC in view; sea in view; `$6298` gate; HUD message: **all identical** (section 7) |
| Moving frames | skip never fires (`NSKIP = 0` over 100 flips walking / banked turn / turning); cost 2.5 k cy/frame (section 8) |

Patches (sites; blob map `$B6000-$B7FFF`):

| Patch | Site | Phase | Blob | Role |
|---|---|---|---|---|
| `p7_skip_render` | `$1dbbe` (10 B) | deferred | `$B7500` (replay of the displaced pair), `$B7510-$B7933` (hook, `OBJPASS`, `MKCMP`, `MKCOPY`); data `$B6000-$B747F` | the predicate and the skip |
| `p7_skip_scn` | `$1dc12` (6 B) | deferred | `$B7C40` | scene renderer entered from anywhere but `$1dbe2` clears the snapshots; from `$1dbe2` sets `SCN` |
| `p7_skip_gate` | `$1b6be` (8 B) | deferred | `$B7C80` | gate path paints the window: clear the snapshots |
| `p7_skip_enter` | `$28cf6` (8 B) | boot | `$B7CC0` | 3D-view (re)entry: clear the snapshots |
| `p7_skip_wv1/2/3` | `$1dafc`, `$1fd1c`, `$1fd9a` (8 B each) | deferred | `$B7D00/20/40` | set `WAVE` where the render reads the wave table pointer `$1dfba` |

Gate command lines: `python3 tools/mw2patch.py live --only <p4+p7 defaults> p7_skip_render p7_skip_scn p7_skip_gate p7_skip_enter p7_skip_wv1 p7_skip_wv2 p7_skip_wv3 --out /tmp/sk/basesk`
(the base set is the same list without the seven `p7_skip_*`); `work/p7_skip/run_gates.sh`.

## 1. The rule (double buffer)

The game draws the 3D window into the back buffer `$67a6` (`$60000` or `$70000`), flips (`$315c6 jsr $4f36`), and draws the other one next. A snapshot of the render inputs is
kept **per buffer**: `SC[b]`, `OBJ[b]`, `MK[b]`, `VAL[b]`, `WV[b]`, `WP[b]`, `SCNR[b]` (`b = bit 16 of $67a6`). `VAL[b] = 1` means: the picture now in buffer `b` was rendered from exactly
those inputs. The hook runs at the render entry; if the inputs equal `SNAP[b]` the renderer returns at once and the buffer is presented as it is. That is "the last two presented frames
used the same inputs" without a separate counter: after any change both buffers are rendered once (`NREND = 4` in the first standing gate: two scalar-changed records, two full records),
then every frame is skipped (`NSKIP = 95` at flip 100).

Everything else of the frame runs as before: HUD gauges (`$3158c jsr $50b0` = `p3b_render`), view setup (`$315a0 jsr $5086`), the post-render calls (`$315a8-$315c0`),
flip, post-flip. The hook is entered through `jsr $5056` (stub `jmp $1dbbe.l`), so `(a7) = $315a8` identifies the main loop; the other caller (`$325d8`, `$32598`) is rendered
normally and clears `VAL[]`.

Why the old picture is still valid in the window (rows 58-199 of the back buffer): **only the renderer writes those rows.**
`work/p7_skip/scrscan.py` over seven whole-loop instruction traces (`trace cpu_disasm`, 35 iterations: standing, NPC near, NPC far, sea view, walking, banked turn, firing):
```
tn_foot.txt iterations 3 | writes into rows >= 58 outside the render: NONE | rows<58 writes by phase {'pre': 12384}
tn_npc.txt iterations 2 | ... NONE | {'pre': 8272}      tn_npc2.txt iterations 7 | NONE | {'pre': 28952}
tn_sea.txt iterations 4 | NONE | {'pre': 18976}         tn_walk.txt iterations 5 | NONE | {'pre': 34720}
tn_bank.txt iterations 5 | NONE | {'pre': 42544}        tn_fire.txt iterations 9 | NONE | {'pre': 40008}
```
(`pre` = the HUD gauge/sprite/radar code before the render, rows 4-49.) The exceptions are all handled:

| Writer into the window outside `$1dbbe` | Handling |
|---|---|
| HUD message boxes `$3264a`/`$326de`/`$32910` (timers `$7590/$7582/$759c`; text at `(x,y) = (10,$46)` and `($a0,$46)`, y = 70 is a window row; `jsr $4eee`/`$4ed0` after the render) | no skip while any timer is >= 0 (`tst.w ; bpl`), and `VAL[]` is cleared, so the text is erased by a full render after it ends. Test: `$7590 = 5` poked, `msg.txt`: `NUNS` 1..5, picture identical, screenshot shows "Trap triggered 4" inside the window |
| `$326de` with `$7582 = 0`, `$32910` with `$759c = 0`: nested loops that call `$327e6` (alternate scene render `$328e2 jsr $505c`) and flip by themselves | `$505c` entered from anywhere but `$1dbe2` clears `VAL[]` (`p7_skip_scn`) |
| render gate `$6298` (toggled by the debug key `$52`, `$1b3c6 not.w $6298`): `$31596 jsr $5098` -> `$1b6be` paints the window area | `p7_skip_gate` clears `VAL[]`. Test: `gate6298.txt` (`$6298` on at flip 10, off at 14): `NINV 0 -> 4`, identical |
| 3D (re)entry `$28cc0` (callers `$31632/$32ebc/$33016`) re-encodes the cockpit list and may change the screens | `p7_skip_enter` at `$28cf6`, the tail common to both paths (the path through `$28cee jsr $30e30` and the `bmi.b $28cf6` path for types with no cockpit picture) |
| `$32598` (`jsr $5086 ; jsr $5056` at `$325d8`, callers `$32474/$3304c/$33496/$335b2`) | `$315a8` test in the hook: other callers clear `VAL[]` |
| any type but the foot type 13, or `$40b6 <> 0` | no skip, `VAL[]` cleared |

## 2. Cockpit replay and `p4_hud_pfx_*` / `p7_ck_*` with a skipped render

The replay `$30f2c` runs inside `$1dbbe` (`$1dc0c jsr $5002`), so a skipped frame does not replay. That is correct because the replay is idempotent
(`(x & mask) | or`, `cockpit.md` 4C) and the buffer already holds `sky + terrain + replayed cockpit` of an identical render. State of the clean-prefix set that lives
outside the buffers: `KB[b]` (clean 8-line blocks of buffer b) describes buffer b only and a skip leaves buffer b untouched; `YMIN` is reset by every sky fill (`p4_hud_pfx_fill`) and
only read by the replay of the same render; `p7_ck_*` state (`EN`, `BUILT`, table) is per render and per 3D entry. None of it carries across a skipped frame.
The EN/BUILT table is rebuilt by the encoder at 3D entry, where `p7_skip_enter` also clears `VAL[]`.

Pixel evidence with all of them live in both runs (A = p4 + p7 cell + p7 ck, B = A + p7_skip, `a_base.txt`):
```
flip   10: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), ... 'NSKIP': 5, 'NREND': 4, ...}
flip   40: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), ... 'NSKIP': 35, 'NREND': 4, ...}
flip  100: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), ... 'NSKIP': 95, 'NREND': 4, ...}
1mb_ingame_foot fa1 IDENTICAL
```
and against the UNPATCHED game (`a_unpatched.txt`: A = nothing live) the same three lines and `fa2 IDENTICAL`. The stop-and-go run (section 7) is the transition proof:
the cockpit/prefix state is exercised when a skipped buffer is rendered again (heading poked at flip 18, position at 43, restore at 68, every transition captured).
A prefix-set-only run (A = unpatched, B = `p4_hud_pfx_*` + `p4_hud_reset` + skip) is in section 7 as well.

## 3. What the 3D render reads (method and result)

Method, with Hatari 2.6.1 (`trace cpu_disasm`, started and stopped by `:once :file` breakpoints, the trace prints the effective address `== $xxxx [value]` of every memory operand):
`work/p7_skip/traceN.py snap out K mem [pokes]` traces K whole loop iterations (`$31486 -> $31486`); `rdset.py` classifies each operand by mnemonic (read, write, read-modify-write,
`movem` register lists) and computes, per iteration, the bytes the renderer (`$5056 -> $315a8`) **reads before it writes them** (the real inputs, i.e. `rbw`), the bytes written by
non-render code (pre-render logic, post-render calls, flip, interrupts), and their intersection (**channels**). Interrupt code is excluded from `rbw` and included in the writers.
Scenes (all unpatched, 1 MB or 2 MB snapshots): standing, NPC poked 1200 units ahead (moving), sea view (player poked 8 cells east, heading east), walking, banked turn, firing.

Raw channel table over 35 iterations (`evidence/channels.txt`: "render rbw bytes 7734, non-render written bytes 1757"):
```
003534-003541   14 ['pre'] wpc ['0x35b14', '0x37e38', ...]  readers ['0x1c516', '0x1c568', '0x20142', '0x20146']   NPC +2..+$f
003548-003549    2 ['pre'] wpc ['0x35b04']                  readers ['0x1c62e']                                   NPC +$16
00354c-00354f    4 ['pre'] wpc ['0x37d32', '0x37d36']       readers ['0x1c52e', '0x1c534']                        NPC +$1a,+$1c
003566-003567    2 ['pre'] wpc ['0x325f6']                  readers ['0x1c53a']                                   NPC +$34
0053ac-0053af    4 ['pre'] wpc ['0x37ad8', '0x37adc']       readers ['0x1c3cc', '0x1c3d0']
0066e6-0066ed    8 ['pre'] wpc ['0x34504', '0x34508']       readers ['0x1dbbe', '0x1dbc8']                        position
00670a-00670d    4 ['pre'] wpc ['0x37b0e', '0x37b12']       readers ['0x200de', '0x200e2']                        cell
0067a6-0067a9    4 ['post'] wpc ['0x26eb8']                 readers ['0x1b99a']                                   draw buffer (= the index b)
00763e-007645    8 ['pre'] wpc ['0x34782', ...]             readers ['0x1dd22', '0x1dd26', '0x1dd3a', '0x1dd3e']
00764a-00764d    4 ['pre'] wpc ['0x33f7a', '0x345f6']       readers ['0x1c33a', '0x1dbd8']                        heading mirror, altitude
007652-007655    4 ['pre'] wpc ['0x34774', '0x3477c']       readers ['0x1c31e', '0x1c322']
017fc4-017fc5    2 ['pre'] wpc ['0x3257e']                  readers ['0x3bc62']
018768-018769    2 ['pre'] wpc ['0x202be']                  readers ['0x1d88e']
018772-018779    8 ['pre'] wpc ['0x2029e', '0x202a6', '0x202ae', '0x202b6'] readers [...]                          draw distance / fog band
018784-018785    2 ['pre'] wpc ['0x2027c']                  readers ['0x1dc22']
018788-018789    2 ['pre'] wpc ['0x20298']                  readers ['0x1dc28']
018796-018797    2 ['pre'] wpc ['0x20312']                  readers ['0x1dd08']
```
`$20272` (the `jsr $5086` at `$315a0`, `m68dis 20272`) writes the view constants right before every render: `$18784 = $66e6-$6400` (`$2027c`), `$18786 = $764c` (`$20286`), `$18788 = -($66ea-$6400)` (`$20298`),
the four draw distances `$18772-$18778 = $a90/$900/$790/$640` (`$2029e-$202b6`), `$18768` (`$202be` sets 1; `$202e0` sets 0, with draw distances `$510/$400/$310/$240`, when the wave-aware height `jsr $506e` at `$202d2` is not below `$764c`), and the three
view angles `$18796/$18798/$1879a = ($6742>>1)+$100, $6746>>1, $674a>>1` (`$20308-$2032a`). The render reads the derived words, so they (not `$6742/$6746/$674a`) are the inputs.

### The signature (`SC`, 104 bytes staged at `$B6110`, compared with `cmpm.l`)
| Words | What | Evidence |
|---|---|---|
| `$6220` | type | `$1dbee cmpi.w #$5,$6220` (and the 5/`$15`/`$11` branch); hook precondition `= 13` |
| `$66e0` | cell scale | `$200ce move.w $66e0.w,d7 ; divs.w d7,d0` (`$200b4`, `$20136`, `$201ac`) |
| `$66e6/$66ea` (2 longs) | player position | `$1dbbe/$1dbc8`; written by the integrator `$34504/$34508` |
| `$670a/$670c` | player cell | `$200de/$200e2`; written `$37b0e/$37b12` |
| `$6f78` | marker count | `$200be move.w $6f78.w,d6` |
| `$67be` | vertex shade shift | `$1dcd2 move.w $67be.w,d0 ; asr.w d0,d2` |
| `$6806` | fill parameter | `$38ca6 move.w $6806.w,d3` (read before written in the standing, walking, banked, firing and NPC traces; never written by the render, `m68dis --xref 6806`: no writer; constant 0 in every dump) |
| `$763e-$7661` (36 B) | view matrix, lean, throttle trig, `$764a` heading mirror, `$764c` altitude, `$7652/$7654`, `$765a-$7660` | `$1dd22-$1dd3e`, `$1c318-$1c34e`, `$1c4cc-$1c4e0`, `$1dbd8`; writers `$34774-$347ea`, `$33f7a`, `$345f6`, `$32090-$320a2` |
| `$17fc4` | focal copy | `$3bc62`; writer `$3257e` |
| `$18768` | below-wave flag | `$1d88e`, `$1c4aa`; writer `$202be/$202e0` |
| `$18556-$18561` (3 longs) | view offset | `$1d484-$1d48c`, `$1e7d8`; changes while walking (dump diff) |
| `$18772-$18779` (2 longs) | draw distances / fog band thresholds | `$1e774`, `$1ec32-$1ec56`; writer `$2029e-$202b6` |
| `$18784`, `$18786`, `$18788` | view origin and altitude | `$1dc22`, `$1dc28`; writers `$2027c-$20298` |
| `$18796`, `$18798`, `$1879a` | heading, bank, pitch | `$1dd08`; writer `$20312-$2032a` |
| `$53ac/$53ae`, `$53da/$53dc` | per-frame object view terms | `$1c3cc/$1c3d0`, `$1c4e2/$1c4e6`; writers `$37ad8/$37adc` |

Not in the signature on purpose: `$6808` (per-polygon scratch written by `$1fa7c move.w (a6)+,$6808.w`, `$38bc0`, `$1c6ac` before it is read; **it toggles 0x24/0x25 every frame
in the sea view**: it was in the first version of `SC` and made the sea view re-render every frame for nothing, `scdump.py` found it), `$1877c` and `$1dfba` (below), `$67a6` (the buffer index).
`cover.py` also verifies the other direction: **the render writes none of the signature bytes** (0 of the 76 + object bytes in 7 traces), so a snapshot taken at the hook cannot be changed by the render itself.

### Object records (`OBJ`, variable length, 1152 B per buffer) and markers (`MK`)
The marker pass `$20088` (m68dis) builds the window list `$7c0d8` from three tables: `$200b4` markers (`$4bfa8` stride 16, count `$6f78`+1, position longs at +$12/+$16, id word at +$20),
`$20136` units (`$3532`, 30 x `$42`, skipped when `tst.w $2e(a0)` is negative, position `+6/+a`), `$201ac` effects (`$3cee`, 30 x `$18`, skipped when `tst.w (a0)` is negative, position `+4/+a`). Only records
within +-8 cells of `$670a/$670c` are inserted (`cmp.w #$8/#$fff8` at `$200e8-$20104`, `$20164-$20180`, `$201d8-$201f4`).
* **Units**: the draw `$1c3fc` (NPC branch `$1c508`) reads (m68dis, confirmed per byte in the NPC trace): `+0`, `+2` (model pointer), `+6`, `+$a` (position), `+$e`, `+$16`, `+$1a`, `+$1c`, `+$1e`, `+$20`, `+$2c`, `+$2e` (also
  `$1c6d8` via `a5`), `+$34`. The hook stores the word `$2e` of every unit (negative = inactive); for an active one a marker `$7ffe` (outside the window) or `$7fff` plus those 15 words (inside). The window test is
  `|x-$66e6| <= 16*$66e0` and `|y-$66ea| <= 16*$66e0` (long arithmetic, no divides): a superset of the game's +-8 cells (rounding of the two divisions is at most 2 cells), so
  an active unit that cannot be drawn does not force renders (`npc_radius.txt`: units poked 2000-8000 units away move continuously, units poked 9000 and 12000 away were idle for 4 s and then appeared next to the player). A unit with `$2e = 0` inside the window takes the `$1c64e jsr $50a4` path: not modelled, **no skip**.
* **Effects**: the flag word, and `$7ffe` for an active one outside the window; **an active effect inside the window means no skip** (explosions/impacts animate; the `$50aa` path reads `$3fbe` tables and `$180e6..`).
* **Markers**: the 16-byte records `[$4bfba + 16 i]`, `i <= $6f78`, compared whole (X.l, Y.l, 3 unread bytes, type byte `$1d(a5,d0)`, word `$1e`, id `$20`): `$4bfba-$4c33a` for 56 records. At most 80 records (`MKMAX`); more means no skip.
  Static scenery today (`mk` rows in the standing dump), but `$32afa`, `$32b8a`, `$353d8`, `$35fbc` ... also address the table (`m68dis --xref 4bfa8`), so it is compared, not assumed.

### The wave phase (`$1dfba`), the sea animation
`movea.l $1dfba(pc),aN` is executed at `$1db04` (terrain water vertices, inside the render), `$1fd1c` (`$506e`, called inside the render by `$1c59a` for units) and `$1fd9a` (`$507a`). The pointer
`$1dfba = $18574 + $1877c` advances by 8 (mod `$80`) in `$1dcae-$1dcca` after every render, so it differs every frame and cannot be part of `SC` (the standing view would never repeat).
`p7_skip_wv1/2/3` set `WAVE` where the table is read; the hook clears `WAVE` before the render and stores it per buffer (`WV[b]`) together with the pointer used (`WP[b]`). A buffer whose picture touched
the table is skipped only if `$1dfba` is unchanged, i.e. never (the phase moves every render): **the sea animates**. Evidence: sea view (`c_sea.txt`): `WV = (1,1)`, `NSKIP = 0`, `NWAV` grows every frame; unit near: `WV` 1 while it is
within the height-probe range. When the table was not touched, the image cannot depend on the phase: in the unpatched game the standing picture is bit-identical at flips 6, 7, 20, 21 and 41 (five different phases of the 16) for each of the headings
0, 256, 512, 768 (`headscan.py`, raw: `e7334c5f`, `5ee9152d`, `902827bb`, `516d1b6c` for every flip and both buffers).

### Render state carried to the next frame
`carried.py` (read then written by the render): only `$1877c` (`addq.w #8,$1877c` at `$1dcae`) and `$1dfba` (`move.l a0,$1dfba` at `$1dcca`) in all 7 traces. Nothing consumes render output outside the render except
`$1dfba` (`outputs.py`: written by the render and read by non-render code: `$1dfba` at `$1fd1c`, the `$20272` height probe). A skip therefore **replays `$1dcae-$1dcca`** (so the wave phase, and with it
the `$20272` decision `$18768`, evolves exactly as in the unpatched game), unless the unpatched render would have skipped it: `$1dbbe` takes `bgt.b $1dbe4` (camera below the terrain) without
`$505c`; `p7_skip_scn` records that (`SCN`, per buffer `SCNR`).

### Coverage check
`cover.py` (all 35 iterations):
```
iterations 35 render-read bytes 7372 also written outside the render 76 covered 72 UNCOVERED 4
  0067a6-0067a9 4 read by pc 1b99a written outside render by post pc 26eb8 (tn_foot.txt)
```
(the only uncovered bytes are the draw-buffer pointer, which is the index of the per-buffer snapshots). The other 7,296 bytes the render reads are never written outside it in 35 iterations: the
terrain `$40040...`, models `$3ac36-$3be3d`, sin table `$44a4-$48a4`, `$51ce..`, `$55876`, `$57054`, the cockpit list `$68000-$69a4d` (constant per 3D entry, `p7_skip_enter`), grid scratch `$6c000-$6e8xx` and slot cache `$7c7xx`
(written by the render before use or by `$1d768`), and stack (`$7d00-$8100`, excluded).

## 4. Predicate (what the hook does, `patches/p7_skip_render.s`)
1. `(a7) = $315a8`, `$6220 = 13`, `$40b6 = 0`, `$7590/$7582/$759c < 0`, `$6f78 < 80`, else render and clear `VAL[]` (counters `NINV`/`NUNS`).
2. Stage the 104 scalar bytes at `$B6110`; `cmpm.l` against `SC[b]` (early exit). Different: `SC[b] := stage`, `VAL[b] := 0`, render (`NSC`; walking: 2.5 k cy overhead, no object work).
3. Same scalars but `VAL[b] = 0` (first frame after the scalars settled): `OBJPASS` and `MKCOPY` record the object parts, `VAL[b] := 1`, render (`NOBJ`).
4. `VAL[b] = 1`, `WV[b]`: `$1dfba <> WP[b]` renders (`NWAV`). `OBJPASS` (compare + write through) or `MKCMP` differs: render (`NOBJ`, snapshot refreshed). Effect or state-0 unit in the window: `VAL[b] := 0`, render (`NUNS`).
5. Everything equal: `NSKIP++`, replay of `$1dcae-$1dcca` if `SCNR[b]`, `rts`.
After a render: `WV[b] := WAVE`, `WP[b] := $1dfba` as it was before the render, `SCNR[b] := SCN`.
Invalidation (`clr.l VAL`, `NINV++`): the four hooks of section 1. Initial data is zero (payload zero at staging), so the first render of each buffer is always done.

## 5. Interaction with p3b / p5
p3b foot sub-ticks reach `$3158c -> ... -> $315a4` when on time; a skipped sub-tick costs the hook (13.7 k cy), the HUD gauge draw and the player sim; the frame limiter then waits for the next 2-VBL tick, so a
standing foot player presents 25 fps of an unchanged window (`501` flips per 1000 VBL cold boot). A pass with `SKIP = 1` never reaches `$315a4`. The world tick (5 Hz) changes units, markers, message timers
and clock; those are in the predicate (units/markers) or in the HUD (clock/gauges), so a quiet standing view skips the world-tick frames too (`NSKIP` kept rising across them in the cold boot).

## 6. Counters (`D = $B6000`, for the gates)
`VAL.w[2] +0`, `WV.w[2] +4`, `WP.l[2] +8`, `WAVE.w +$10`, `NSKIP.l +$14`, `NREND +$18`, `NINV +$1c`, `WPTMP +$20`, `NUNS +$24`, `NSC +$28`, `NOBJ +$2c`, `NWAV +$30`, `SCNR.w[2] +$34`, `SCN.w +$38`. `m $b6000 64`.

## 7. Gates (raw; `work/p7_skip/evidence/*.txt`)

Pixel gates compare the 32000 visible bytes of both buffers (`$60000`, `$70000`) after the stated flip counts, two Hatari instances, the same snapshot, the live set applied at the same flip (per-frame simulation, no tick/p3b/p5).
"B counters" are the p7_skip counters at that flip (cumulative since the apply flip). Raw files: `work/p7_skip/evidence/`.

### (a) standing, `1mb_ingame_foot`
```
== (a) standing 1mb_ingame_foot: A = p4+p7 base, B = base + p7_skip
flip   10: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 5, 'NREND': 4, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400
flip   40: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 35, 'NREND': 4, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400
flip  100: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 95, 'NREND': 4, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400
1mb_ingame_foot fa1 IDENTICAL

== (a) standing 1mb_ingame_foot: A = UNPATCHED, B = base + p7_skip
flip   10: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 5, 'NREND': 4, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400
flip   40: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 35, 'NREND': 4, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400
flip  100: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 95, 'NREND': 4, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400
1mb_ingame_foot fa2 IDENTICAL

== (a) standing ingame_lobos_foot (2 MB): A = base, B = base + p7_skip
flip   10: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 5, 'NREND': 4, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400
flip   40: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 35, 'NREND': 4, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400
flip  100: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 95, 'NREND': 4, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400
ingame_lobos_foot fa3 IDENTICAL
```

### (b) walking, banked turn, turning (the skip must not fire)
```
== (b) walking 1mb_ingame_walking: A = base, B = base + p7_skip
flip   10: visible differing bytes (both buffers) =      0   B counters {'VAL': (0, 0), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 0, 'NREND': 9, 'NINV': 0, 'NUNS': 0, 'NSC': 9, 'NOBJ': 0, 'NWAV': 0}   pos 000023a000006400
flip   40: visible differing bytes (both buffers) =      0   B counters {'VAL': (0, 0), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 0, 'NREND': 39, 'NINV': 0, 'NUNS': 0, 'NSC': 39, 'NOBJ': 0, 'NWAV': 0}   pos 00001d2e00006400
flip  100: visible differing bytes (both buffers) =      0   B counters {'VAL': (0, 0), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 0, 'NREND': 98, 'NINV': 0, 'NUNS': 0, 'NSC': 98, 'NOBJ': 0, 'NWAV': 0}   pos 0000608100006400
1mb_ingame_walking fb1 IDENTICAL

== (b) banked turn ingame_foot_banked_turn (2 MB): A = base, B = base + p7_skip
flip   10: visible differing bytes (both buffers) =      0   B counters {'VAL': (0, 0), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 0, 'NREND': 9, 'NINV': 0, 'NUNS': 0, 'NSC': 9, 'NOBJ': 0, 'NWAV': 0}   pos 00005ac6000063cb
flip   40: visible differing bytes (both buffers) =      0   B counters {'VAL': (0, 0), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 0, 'NREND': 39, 'NINV': 0, 'NUNS': 0, 'NSC': 39, 'NOBJ': 0, 'NWAV': 0}   pos 00005adf00006330
flip  100: visible differing bytes (both buffers) =      0   B counters {'VAL': (0, 0), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 0, 'NREND': 99, 'NINV': 0, 'NUNS': 0, 'NSC': 99, 'NOBJ': 0, 'NWAV': 0}   pos 00005aa400006315
ingame_foot_banked_turn fb2 IDENTICAL

== (b) turning ingame_foot_turning (2 MB)
flip   10: visible differing bytes (both buffers) =      0   B counters {'VAL': (0, 0), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 0, 'NREND': 9, 'NINV': 0, 'NUNS': 0, 'NSC': 9, 'NOBJ': 0, 'NWAV': 0}   pos 00005b1b00006400
flip   40: visible differing bytes (both buffers) =      0   B counters {'VAL': (0, 0), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 0, 'NREND': 39, 'NINV': 0, 'NUNS': 0, 'NSC': 39, 'NOBJ': 0, 'NWAV': 0}   pos 0000586900006400
flip  100: visible differing bytes (both buffers) =      0   B counters {'VAL': (0, 0), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 0, 'NREND': 99, 'NINV': 0, 'NUNS': 0, 'NSC': 99, 'NOBJ': 0, 'NWAV': 0}   pos 0000530500006400
ingame_foot_turning fb3 IDENTICAL
```
Fire count: `NSKIP = 0` at every capture; every frame took the scalar-changed path (`NSC = NREND`).

### stop-and-go (every transition into and out of a skipped state, with the whole default P7 set live)
```
== stop-and-go: heading poke @18, position poke @43, restore @68 (standing snapshot)
flip   19: visible differing bytes (both buffers) =      0   B counters {'VAL': (0, 1), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 13, 'NREND': 5, 'NINV': 0, 'NUNS': 0, 'NSC': 3, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400
flip   20: visible differing bytes (both buffers) =      0   B counters {'VAL': (0, 0), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 13, 'NREND': 6, 'NINV': 0, 'NUNS': 0, 'NSC': 4, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400
flip   22: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 13, 'NREND': 8, 'NINV': 0, 'NUNS': 0, 'NSC': 4, 'NOBJ': 4, 'NWAV': 0}   pos 0000640000006400
flip   25: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 16, 'NREND': 8, 'NINV': 0, 'NUNS': 0, 'NSC': 4, 'NOBJ': 4, 'NWAV': 0}   pos 0000640000006400
flip   44: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 0), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 34, 'NREND': 9, 'NINV': 0, 'NUNS': 0, 'NSC': 5, 'NOBJ': 4, 'NWAV': 0}   pos 0000670000006400
flip   45: visible differing bytes (both buffers) =      0   B counters {'VAL': (0, 0), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 34, 'NREND': 10, 'NINV': 0, 'NUNS': 0, 'NSC': 6, 'NOBJ': 4, 'NWAV': 0}   pos 0000670000006400
flip   47: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 34, 'NREND': 12, 'NINV': 0, 'NUNS': 0, 'NSC': 6, 'NOBJ': 6, 'NWAV': 0}   pos 0000670000006400
flip   69: visible differing bytes (both buffers) =      0   B counters {'VAL': (0, 1), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 55, 'NREND': 13, 'NINV': 0, 'NUNS': 0, 'NSC': 7, 'NOBJ': 6, 'NWAV': 0}   pos 0000640000006400
flip   70: visible differing bytes (both buffers) =      0   B counters {'VAL': (0, 0), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 55, 'NREND': 14, 'NINV': 0, 'NUNS': 0, 'NSC': 8, 'NOBJ': 6, 'NWAV': 0}   pos 0000640000006400
flip   72: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 55, 'NREND': 16, 'NINV': 0, 'NUNS': 0, 'NSC': 8, 'NOBJ': 8, 'NWAV': 0}   pos 0000640000006400
flip   90: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 73, 'NREND': 16, 'NINV': 0, 'NUNS': 0, 'NSC': 8, 'NOBJ': 8, 'NWAV': 0}   pos 0000640000006400
1mb_ingame_foot sg1 IDENTICAL
```
and with only the clean-prefix set, or only the cull set, live, against the UNPATCHED game (tail of each):
```
flip   70: visible differing bytes (both buffers) =      0   B counters {'VAL': (0, 0), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 55, 'NREND': 14, 'NINV': 0, 'NUNS': 0, 'NSC': 8, 'NOBJ': 6, 'NWAV': 0}   pos 0000640000006400
flip   72: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 55, 'NREND': 16, 'NINV': 0, 'NUNS': 0, 'NSC': 8, 'NOBJ': 8, 'NWAV': 0}   pos 0000640000006400
flip   90: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 73, 'NREND': 16, 'NINV': 0, 'NUNS': 0, 'NSC': 8, 'NOBJ': 8, 'NWAV': 0}   pos 0000640000006400
1mb_ingame_foot sg_pfxsk IDENTICAL
flip   70: visible differing bytes (both buffers) =      0   B counters {'VAL': (0, 0), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 55, 'NREND': 14, 'NINV': 0, 'NUNS': 0, 'NSC': 8, 'NOBJ': 6, 'NWAV': 0}   pos 0000640000006400
flip   72: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 55, 'NREND': 16, 'NINV': 0, 'NUNS': 0, 'NSC': 8, 'NOBJ': 8, 'NWAV': 0}   pos 0000640000006400
flip   90: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 73, 'NREND': 16, 'NINV': 0, 'NUNS': 0, 'NSC': 8, 'NOBJ': 8, 'NWAV': 0}   pos 0000640000006400
1mb_ingame_foot sg_cksk IDENTICAL
```

### (c) something moves while the player stands (unit poked into the NPC table, `$2e = 1`, state 0; its own AI moves it)
Near unit, 2224 units ahead (inside the window, visible as a small figure), moving; the skip must not freeze it:
```
== (c1) NPC poked 1200 units ahead, moving, player standing
flip    6: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (1, 1), 'WAVE': 1, 'NSKIP': 0, 'NREND': 5, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 1}   pos 0000640000006400 npc0 x=23346 y=25603
flip    7: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (1, 1), 'WAVE': 1, 'NSKIP': 0, 'NREND': 6, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 2}   pos 0000640000006400 npc0 x=23316 y=25608
flip    8: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (1, 1), 'WAVE': 1, 'NSKIP': 0, 'NREND': 7, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 3}   pos 0000640000006400 npc0 x=23276 y=25615
flip    9: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (1, 1), 'WAVE': 1, 'NSKIP': 0, 'NREND': 8, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 4}   pos 0000640000006400 npc0 x=23226 y=25624
flip   10: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (1, 1), 'WAVE': 1, 'NSKIP': 0, 'NREND': 9, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 5}   pos 0000640000006400 npc0 x=23167 y=25635
flip   14: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (1, 1), 'WAVE': 1, 'NSKIP': 0, 'NREND': 13, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 9}   pos 0000640000006400 npc0 x=22882 y=25687
flip   20: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 0, 'NREND': 19, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 15}   pos 0000640000006400 npc0 x=22450 y=25765
flip   30: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 0, 'NREND': 29, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 12, 'NWAV': 15}   pos 0000640000006400 npc0 x=22157 y=26159
flip   40: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (1, 1), 'WAVE': 1, 'NSKIP': 0, 'NREND': 39, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 19, 'NWAV': 18}   pos 0000640000006400 npc0 x=22866 y=26058
1mb_ingame_foot npc1 IDENTICAL
```
Screenshots (`gate.py --png`, buffer `$60000` of A = base and B = base + skip at the captured flips): `/tmp/sk/g/npc1/{A,B}_{6..40}_60000.png`; the figure moves between flips in both and the two are identical (0 differing bytes above).

Unit active but 17400 units away (outside the 16-cell window, AI idle there: `npc0` does not move) and then a far unit repositioned by poke at flips 10/14/18/22 (always > 13000 units away); the skip keeps firing, the picture is identical:
```
== (c2) NPC poked 17400 units away (outside the 16-cell window), moving
flip    6: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 1, 'NREND': 4, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400 npc0 x=8192 y=25600
flip   10: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 5, 'NREND': 4, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400 npc0 x=8192 y=25600
flip   20: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 15, 'NREND': 4, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400 npc0 x=8192 y=25600
flip   30: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 25, 'NREND': 4, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400 npc0 x=8192 y=25600
flip   40: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 35, 'NREND': 4, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400 npc0 x=8192 y=25600
flip   60: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 55, 'NREND': 4, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400 npc0 x=8192 y=25600
1mb_ingame_foot npc2 IDENTICAL

flip    6: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 1, 'NREND': 4, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400 npc0 x=8192 y=25600
flip   12: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 7, 'NREND': 4, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400 npc0 x=5376 y=28672
flip   16: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 11, 'NREND': 4, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400 npc0 x=2560 y=20480
flip   20: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 15, 'NREND': 4, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400 npc0 x=6144 y=10752
flip   26: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 21, 'NREND': 4, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400 npc0 x=12288 y=40960
flip   30: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 25, 'NREND': 4, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400 npc0 x=12288 y=40960
flip   40: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 35, 'NREND': 4, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400 npc0 x=12288 y=40960
1mb_ingame_foot npc3 IDENTICAL
```
Unit movement radius (`npcrad.py`: six units poked at 2000..12000 units, positions 4 s apart):
```
dist 2000 start (23250, 25661) +4s (22593, 26147) +8s (23849, 25859) MOVED
dist 4000 start (21844, 25514) +4s (20662, 24923) +8s (21098, 24391) MOVED
dist 6000 start (19547, 25428) +4s (21006, 25256) +8s (22264, 25229) MOVED
dist 8000 start (17669, 25478) +4s (17945, 24727) +8s (19193, 24494) MOVED
dist 9000 start (16600, 25600) +4s (16600, 25600) +8s (25624, 25595) MOVED
dist 12000 start (13600, 25600) +4s (13600, 25600) +8s (22977, 24990) MOVED
```
Sea in view (player 8 cells east, heading east; the sea cells use the wave table): the picture is identical, `WV = (1,1)`, `NSKIP = 0`, `NWAV` rises: the animated sea is never skipped:
```
== (c3) sea in view (player moved 8 cells east, heading east)
flip    6: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (1, 1), 'WAVE': 1, 'NSKIP': 0, 'NREND': 5, 'NINV': 0, 'NUNS': 0, 'NSC': 3, 'NOBJ': 2, 'NWAV': 0}   pos 000075f800006400 npc0 x=0 y=0
flip    7: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (1, 1), 'WAVE': 1, 'NSKIP': 0, 'NREND': 6, 'NINV': 0, 'NUNS': 0, 'NSC': 3, 'NOBJ': 2, 'NWAV': 1}   pos 000075f800006400 npc0 x=0 y=0
flip    8: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (1, 1), 'WAVE': 1, 'NSKIP': 0, 'NREND': 7, 'NINV': 0, 'NUNS': 0, 'NSC': 3, 'NOBJ': 2, 'NWAV': 2}   pos 000075f800006400 npc0 x=0 y=0
flip    9: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (1, 1), 'WAVE': 1, 'NSKIP': 0, 'NREND': 8, 'NINV': 0, 'NUNS': 0, 'NSC': 3, 'NOBJ': 2, 'NWAV': 3}   pos 000075f800006400 npc0 x=0 y=0
flip   10: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (1, 1), 'WAVE': 1, 'NSKIP': 0, 'NREND': 9, 'NINV': 0, 'NUNS': 0, 'NSC': 3, 'NOBJ': 2, 'NWAV': 4}   pos 000075f800006400 npc0 x=0 y=0
flip   11: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (1, 1), 'WAVE': 1, 'NSKIP': 0, 'NREND': 10, 'NINV': 0, 'NUNS': 0, 'NSC': 3, 'NOBJ': 2, 'NWAV': 5}   pos 000075f800006400 npc0 x=0 y=0
flip   20: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (1, 1), 'WAVE': 1, 'NSKIP': 0, 'NREND': 19, 'NINV': 0, 'NUNS': 0, 'NSC': 3, 'NOBJ': 2, 'NWAV': 14}   pos 000075f800006400 npc0 x=0 y=0
flip   21: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (1, 1), 'WAVE': 1, 'NSKIP': 0, 'NREND': 20, 'NINV': 0, 'NUNS': 0, 'NSC': 3, 'NOBJ': 2, 'NWAV': 15}   pos 000075f800006400 npc0 x=0 y=0
flip   40: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (1, 1), 'WAVE': 1, 'NSKIP': 0, 'NREND': 39, 'NINV': 0, 'NUNS': 0, 'NSC': 3, 'NOBJ': 2, 'NWAV': 34}   pos 000075f800006400 npc0 x=0 y=0
1mb_ingame_foot sea1 IDENTICAL
```
Other writers of the window: the render gate `$6298` (on at flip 10, off at 14) and a HUD message (`$7590 = 5`, text drawn into the window after the render):
```
== render gate $6298 on at flip 10, off at flip 14
flip    8: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 3, 'NREND': 4, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400 npc0 x=0 y=0
flip   11: visible differing bytes (both buffers) =      0   B counters {'VAL': (0, 0), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 5, 'NREND': 4, 'NINV': 1, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400 npc0 x=0 y=0
flip   13: visible differing bytes (both buffers) =      0   B counters {'VAL': (0, 0), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 5, 'NREND': 4, 'NINV': 3, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400 npc0 x=0 y=0
flip   15: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 0), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 5, 'NREND': 5, 'NINV': 4, 'NUNS': 0, 'NSC': 2, 'NOBJ': 3, 'NWAV': 0}   pos 0000640000006400 npc0 x=0 y=0
flip   16: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 5, 'NREND': 6, 'NINV': 4, 'NUNS': 0, 'NSC': 2, 'NOBJ': 4, 'NWAV': 0}   pos 0000640000006400 npc0 x=0 y=0
flip   18: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 7, 'NREND': 6, 'NINV': 4, 'NUNS': 0, 'NSC': 2, 'NOBJ': 4, 'NWAV': 0}   pos 0000640000006400 npc0 x=0 y=0
flip   24: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 13, 'NREND': 6, 'NINV': 4, 'NUNS': 0, 'NSC': 2, 'NOBJ': 4, 'NWAV': 0}   pos 0000640000006400 npc0 x=0 y=0
flip   40: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 29, 'NREND': 6, 'NINV': 4, 'NUNS': 0, 'NSC': 2, 'NOBJ': 4, 'NWAV': 0}   pos 0000640000006400 npc0 x=0 y=0
1mb_ingame_foot gt1 IDENTICAL

== HUD message timer $7590 = 5 at flip 10 (text drawn into the window after the render)
flip    8: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 3, 'NREND': 4, 'NINV': 0, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400 npc0 x=0 y=0
flip   11: visible differing bytes (both buffers) =      0   B counters {'VAL': (0, 0), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 5, 'NREND': 4, 'NINV': 0, 'NUNS': 1, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400 npc0 x=0 y=0
flip   12: visible differing bytes (both buffers) =      0   B counters {'VAL': (0, 0), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 5, 'NREND': 4, 'NINV': 0, 'NUNS': 2, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400 npc0 x=0 y=0
flip   14: visible differing bytes (both buffers) =      0   B counters {'VAL': (0, 0), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 5, 'NREND': 4, 'NINV': 0, 'NUNS': 4, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}   pos 0000640000006400 npc0 x=0 y=0
flip   16: visible differing bytes (both buffers) =      0   B counters {'VAL': (0, 1), 'WV': (0, 0), 'WAVE': 0, 'NSKIP': 5, 'NREND': 5, 'NINV': 0, 'NUNS': 5, 'NSC': 2, 'NOBJ': 3, 'NWAV': 0}   pos 0000640000006400 npc0 x=0 y=0
flip   18: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 6, 'NREND': 6, 'NINV': 0, 'NUNS': 5, 'NSC': 2, 'NOBJ': 4, 'NWAV': 0}   pos 0000640000006400 npc0 x=0 y=0
flip   24: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 12, 'NREND': 6, 'NINV': 0, 'NUNS': 5, 'NSC': 2, 'NOBJ': 4, 'NWAV': 0}   pos 0000640000006400 npc0 x=0 y=0
flip   40: visible differing bytes (both buffers) =      0   B counters {'VAL': (1, 1), 'WV': (0, 0), 'WAVE': 1, 'NSKIP': 28, 'NREND': 6, 'NINV': 0, 'NUNS': 5, 'NSC': 2, 'NOBJ': 4, 'NWAV': 0}   pos 0000640000006400 npc0 x=0 y=0
1mb_ingame_foot msg1 IDENTICAL
```

### (d) cold boot of the full default build + p7_skip (`build/p7skip`, `work/p7_skip/boot_skip.py`)
Same session, skip live vs the `p7_skip_render` site restored to its original bytes (`$1dbbe: 203866e604800000 6400`), `h.fps(1000)` = flips per 1000 VBL; the other six hooks stay applied. Walking is a short walk (the cliff 6000 units west of the start turns the player into another type).
**1 MB STE, TOS 1.62** (`boot/ste1mb.log`):
```
3D view: $6220=d $700a=2
MWPO: 000B2FF8: 4d 57 50 4f                                      MWPO
site $1dbbe now: 0001DBBE: 4e f9 00 0b 75 10                                N∙..u. (expect 4e f9 00 0b 75 10)
counters after boot (standing): {'VAL': (1, 1), 'WV': (0, 0), 'NSKIP': 240, 'NREND': 4, 'NINV': 2, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}
STANDING, skip live / reverted (p7_skip_render site), same session:
  skip live: 501 flips / 1000 VBL (25.05 fps)  counter deltas {'NSKIP': 569, 'NREND': 0, 'NINV': 0, 'NUNS': 0, 'NSC': 0, 'NOBJ': 0, 'NWAV': 0}  pos (25600, 25600, 768)
  skip reverted: 95 flips / 1000 VBL (4.75 fps)  counter deltas {'NSKIP': 0, 'NREND': 0, 'NINV': 0, 'NUNS': 0, 'NSC': 0, 'NOBJ': 0, 'NWAV': 0}  pos (25600, 25600, 768)
  skip live: 501 flips / 1000 VBL (25.05 fps)  counter deltas {'NSKIP': 569, 'NREND': 0, 'NINV': 0, 'NUNS': 0, 'NSC': 0, 'NOBJ': 0, 'NWAV': 0}  pos (25600, 25600, 768)
  skip reverted: 95 flips / 1000 VBL (4.75 fps)  counter deltas {'NSKIP': 0, 'NREND': 0, 'NINV': 0, 'NUNS': 0, 'NSC': 0, 'NOBJ': 0, 'NWAV': 0}  pos (25600, 25600, 768)
walk (25600, 25600, 768) -> (25138, 25600, 768) moved
WALKING (300 VBL windows; the walk is kept short: the cliff 6000 units west turns the player into another type):
  skip live: 29 flips / 300 VBL (4.83 fps)  counter deltas {'NSKIP': 0, 'NREND': 40, 'NINV': 0, 'NUNS': 0, 'NSC': 40, 'NOBJ': 0, 'NWAV': 0}  pos (23358, 25600, 768)
  skip reverted: 30 flips / 300 VBL (5.00 fps)  counter deltas {'NSKIP': 0, 'NREND': 0, 'NINV': 0, 'NUNS': 0, 'NSC': 0, 'NOBJ': 0, 'NWAV': 0}  pos (21593, 25600, 768)
after stopping: pos (21206, 25600, 768) -> (21206, 25600, 768) skip delta 201 render delta 0
  staged scalars that changed over 2.4 s: []
  $6220 type 0xd  $40b6 0x0  msg timers 0xffff 0xffff 0xffff  $6298 0x0
TURN: heading 0x300 -> 0x378 turned
after the turn: heading 0x378 -> 0x378 skip delta 126 render delta 0
NPC poked 1200 units ahead of the standing player (moving):
  npc0 x,y 00003538: 00 00 58 cd 00 00 66 3d                          .  counters {'VAL': (1, 1), 'WV': (0, 0), 'NSKIP': 3202, 'NREND': 170, 'NINV': 2, 'NUNS': 0, 'NSC': 132, 'NOBJ': 39, 'NWAV': 0}
  npc0 x,y 00003538: 00 00 52 d6 00 00 68 c4                          .  counters {'VAL': (1, 1), 'WV': (1, 1), 'NSKIP': 3202, 'NREND': 192, 'NINV': 2, 'NUNS': 0, 'NSC': 132, 'NOBJ': 50, 'NWAV': 11}
  npc0 x,y 00003538: 00 00 4c ba 00 00 6b 01                          .  counters {'VAL': (1, 1), 'WV': (1, 1), 'NSKIP': 3202, 'NREND': 209, 'NINV': 2, 'NUNS': 0, 'NSC': 132, 'NOBJ': 50, 'NWAV': 28}
```
**4 MB Mega STE, TOS 2.06** (`boot/mste4mb.log`):
```
3D view: $6220=d $700a=2
MWPO: 000B2FF8: 4d 57 50 4f                                      MWPO
site $1dbbe now: 0001DBBE: 4e f9 00 0b 75 10                                N∙..u. (expect 4e f9 00 0b 75 10)
counters after boot (standing): {'VAL': (1, 1), 'WV': (0, 0), 'NSKIP': 708, 'NREND': 4, 'NINV': 2, 'NUNS': 0, 'NSC': 2, 'NOBJ': 2, 'NWAV': 0}
STANDING, skip live / reverted (p7_skip_render site), same session:
  skip live: 496 flips / 1000 VBL (24.80 fps)  counter deltas {'NSKIP': 577, 'NREND': 0, 'NINV': 0, 'NUNS': 0, 'NSC': 0, 'NOBJ': 0, 'NWAV': 0}  pos (25600, 25600, 768)
  skip reverted: 130 flips / 1000 VBL (6.50 fps)  counter deltas {'NSKIP': 0, 'NREND': 0, 'NINV': 0, 'NUNS': 0, 'NSC': 0, 'NOBJ': 0, 'NWAV': 0}  pos (25600, 25600, 768)
  skip live: 496 flips / 1000 VBL (24.80 fps)  counter deltas {'NSKIP': 577, 'NREND': 0, 'NINV': 0, 'NUNS': 0, 'NSC': 0, 'NOBJ': 0, 'NWAV': 0}  pos (25600, 25600, 768)
  skip reverted: 130 flips / 1000 VBL (6.50 fps)  counter deltas {'NSKIP': 0, 'NREND': 0, 'NINV': 0, 'NUNS': 0, 'NSC': 0, 'NOBJ': 0, 'NWAV': 0}  pos (25600, 25600, 768)
walk (25600, 25600, 768) -> (25014, 25600, 768) moved
WALKING (300 VBL windows; the walk is kept short: the cliff 6000 units west turns the player into another type):
  skip live: 37 flips / 300 VBL (6.17 fps)  counter deltas {'NSKIP': 0, 'NREND': 58, 'NINV': 0, 'NUNS': 0, 'NSC': 58, 'NOBJ': 0, 'NWAV': 0}  pos (23064, 25600, 768)
  skip reverted: 44 flips / 300 VBL (7.33 fps)  counter deltas {'NSKIP': 0, 'NREND': 0, 'NINV': 0, 'NUNS': 0, 'NSC': 0, 'NOBJ': 0, 'NWAV': 0}  pos (21109, 25600, 768)
after stopping: pos (20636, 25600, 768) -> (20636, 25600, 768) skip delta 240 render delta 0
  staged scalars that changed over 2.4 s: []
  $6220 type 0xd  $40b6 0x0  msg timers 0xffff 0xffff 0xffff  $6298 0x0
TURN: heading 0x300 -> 0x378 turned
after the turn: heading 0x378 -> 0x378 skip delta 150 render delta 0
NPC poked 1200 units ahead of the standing player (moving):
  npc0 x,y 00003538: 00 00 5b be 00 00 5f de                          .  counters {'VAL': (1, 1), 'WV': (0, 0), 'NSKIP': 4131, 'NREND': 255, 'NINV': 2, 'NUNS': 0, 'NSC': 202, 'NOBJ': 53, 'NWAV': 0}
  npc0 x,y 00003538: 00 00 5a 90 00 00 5b d8                          .  counters {'VAL': (1, 1), 'WV': (0, 0), 'NSKIP': 4131, 'NREND': 297, 'NINV': 2, 'NUNS': 0, 'NSC': 202, 'NOBJ': 96, 'NWAV': 0}
  npc0 x,y 00003538: 00 00 53 ec 00 00 5f fc                          .  counters {'VAL': (0, 0), 'WV': (1, 1), 'NSKIP': 4131, 'NREND': 337, 'NINV': 2, 'NUNS': 24, 'NSC': 202, 'NOBJ': 112, 'NWAV': 0}
  NPC near, skip live: 129 flips / 1000 VBL (6.45 fps)  counter deltas {'NSKIP': 0, 'NREND': 154, 'NINV': 0, 'NUNS': 18, 'NSC': 0, 'NOBJ': 65, 'NWAV': 71}  pos (20636, 25600, 888)
  NPC near, skip reverted: 101 flips / 1000 VBL (5.05 fps)  counter deltas {'NSKIP': 0, 'NREND': 0, 'NINV': 1, 'NUNS': 0, 'NSC': 0, 'NOBJ': 0, 'NWAV': 0}  pos (20892, 25630, 0)
final counters {'VAL': (0, 0), 'WV': (0, 0), 'NSKIP': 4131, 'NREND': 537, 'NINV': 3, 'NUNS': 101, 'NSC': 202, 'NOBJ': 179, 'NWAV': 71}
RESULT flips/1000VBL standing {'new': [496, 496], 'orig': [130, 130]}
```
Screenshots: `work/p7_skip/boot/{ste1mb,mste4mb}_{stand,walk,turn,stand2,npc0,npc1,npc2}.png`.


## 8. Cost

| cy/frame (20 frames, same frames in every run, `work/p7_skip/cyc.py`, `profile` between the 10th and 30th flip) | unpatched | p4 + p7 default set | + p7_skip |
|---|---:|---:|---:|
| `1mb_ingame_foot` (standing) | 1,898,425 | 1,598,307 | **287,897** (-82.0 % vs p4+p7, -84.8 % vs unpatched) |
| `1mb_ingame_walking` | - | 1,194,282 | 1,196,783 (+2,501 = +0.21 %) |

Raw (`evidence/cyc_stand.txt`, `evidence/cyc_walk.txt`):
```
1mb_ingame_foot base cycles 37968508 over 20 frames = 1898425 cy/frame (6479 addrs)
1mb_ingame_foot /tmp/sk/base cycles 31966144 over 20 frames = 1598307 cy/frame (7021 addrs)
1mb_ingame_foot /tmp/sk/basesk cycles 5757948 over 20 frames = 287897 cy/frame (2812 addrs)
[1898425.4, 1598307.2, 287897.4]
1mb_ingame_walking /tmp/sk/base cycles 23885636 over 20 frames = 1194282 cy/frame (7130 addrs)
1mb_ingame_walking /tmp/sk/basesk cycles 23935656 over 20 frames = 1196783 cy/frame (7236 addrs)
[1194281.8, 1196782.8]
```
The hook on a skipped frame costs 13,768 cy (profile of the hook addresses, 20 frames): stage and scalar compare 1,822, `OBJPASS` (30 units + 30 effects, nothing active) 4,332, `MKCMP` (56 markers x 4 longs) 7,266.
On a moving frame it is stage + first-long mismatch + copy of the 26 scalar longs: +2,501 cy per walking frame, no object work (the object parts are only recorded once the scalars have settled).
What is left of a standing frame (287,897): the pre-render logic block (126 k, `render_audit.md`), the HUD gauge/radar/sprite draw `$19f54` (about 144 k, item 5(b) of the plan), flip, interrupts. Profile pages of the skipped frame:
`$1b000` 70 k (radar `$1b6f4/$1b966`, `$1ba24` probes), `$2b000` 46 k, `$34000` 34 k, `$29000` 28 k, `$36000` 22 k, the hook 13.8 k. Cold-boot frame rates: section 7 (d).

## 9. Known gaps
1. **Constants are assumed, not proven.** The bytes the renderer reads and nothing outside it wrote in 35 traced iterations (terrain heights `$40040-`, object models `$3ac36-$3be3d`, sin table `$44a4-$48a4`,
   `$51ce`, `$5266`, `$55876`, `$57054`, `$17a68`, `$18c48-$18d8b`, the cockpit list) are treated as constant. A writer that never ran in my scenes (terrain damage, a mission script editing models) would be missed.
   The cockpit list is covered by the 3D-entry invalidation, the rest is not.
2. **Foot type only.** `$6220 <> 13` (and `$40b6 <> 0`) always renders. Vehicles have more inputs (pitch, other overlay lists, weapon sights) and were not traced; no vehicle snapshot exists.
3. **Not modelled, therefore never skipped**: an active effect record (`$3cee`) or a unit with `$2e = 0` within 16 cells of the player; more than 80 marker records (`MKMAX`); any HUD message timer >= 0.
   Effect and unit-state-0 draws (`$50aa`, `$50a4`) were not traced because I could not create them without a mission event.
4. **Trace coverage**: 35 loop iterations in 7 scenes. Unit field reads outside the traced branch (`+$16`, `+$1e`, `+$20`, only when `$1c6d0` is true) come from the disassembly of `$1c3fc`, not from a run that took
   the branch; `$67be` (shade shift) was 0 in every scene; effects and the cinematic message loops (`$7582 = 0`, `$759c = 0`) were never run, only read in the disassembly.
5. **Window width**: units/effects are looked at inside 16 x `$66e0` units; the game's own test is +-8 cells of `$670a/$670c` (`$20164-$20180`). The margin (rounding of two `divs`, at most 2 cells) is argued, not measured.
6. **Buffers**: the hook takes the buffer index from bit 16 of `$67a6`; true for `$60000/$70000` on 1, 2 and 4 MB (flip `$26e98` writes only `$ff8201/$ff8203`, `frameloop.md` section 5).
7. **Wave pointer**: the animated sea is never skipped (sea views keep the full cost). The wave read sites are the three pc-relative reads of `$1dfba` found by a linear sweep of `$4000-$60000` (`movea.l $1dfba(pc)` at `$1db04`, `$1fd1c`, `$1fd9a`); no
   other reader exists unless it computes the address.
8. **Floppy build** and a plain ST were not run; the sites are resident or overlay addresses identical on floppy (`floppy.md`), the payload range `$B6000-$B7FFF` is zero at staging.
9. HUD (`$19f54`, 144 k) still redraws every presented frame; the clock/radar/messages are untouched (plan 5(b)).

## 10. Reproduce
```
python3 tools/mw2patch.py live --only <p4+p7 default list> p7_skip_render p7_skip_scn p7_skip_gate p7_skip_enter p7_skip_wv1 p7_skip_wv2 p7_skip_wv3 --out /tmp/sk/basesk   # and the same without p7_skip_* -> /tmp/sk/base
work/p7_skip/run_gates.sh                    # all pixel gates, raw output in work/p7_skip/evidence/
python3 work/p7_skip/gate.py ident work/snapshots/1mb_ingame_foot.sav /tmp/sk/base /tmp/sk/basesk 10,40,100 --tag t   # one gate; --poke 'K:cmd;cmd' pokes RAM at the K-th flip (<= 14 breakpoints in total)
python3 work/p7_skip/traceN.py work/snapshots/1mb_ingame_foot.sav /tmp/tn_foot.txt 4 1024 ; python3 work/p7_skip/cover.py /tmp/tn_foot.txt ...
python3 tools/mw2patch.py build --only <defaults> p7_skip_* --out build/p7skip ; python3 work/p7_skip/boot_skip.py ste1mb ste 162 1024 build/p7skip     # cold boot, 4 MB: mste4mb megaste 206 4096
```
