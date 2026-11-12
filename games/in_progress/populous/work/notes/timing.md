# Populous: the world at 5 turns per real second (fixed rate, 50 and 60 Hz, every machine)

2026-11-12, PopTiming. Hatari 2.6.1; 1 MB STE TOS 1.62 snapshots (`work/snapshots/busy_castles`, `busy_quake_volcano`, `genesis_start`), cold boots of HD and floppy builds (STE 1 MB TOS 1.62, Mega STE 4 MB TOS 2.06, TT 4 MB TOS 3.06 `--mmu true`, Falcon 4 MB TOS 4.04).
Design, structure and gates copy Populous 2 (`../populous-2/work/notes/timing.md`, `pop2_tick*.s`, `tools/p2tick.py`); everything here was re-derived for this game's loop.
Patches (all `; default: no`): `pop_tick`, `pop_tick_render`, `pop_tick_logic`, `pop_tick_flip`, `pop_tick_cmd`, `pop_tick_dot` (the tick; blobs `$C5000-$C56FF`, data `$C6000` + 3680). Test-only: `test_pwalk`, `test_rtog_a`, `test_rtog_b`.
Tool: `tools/poptick.py` (`ab`, `rate`, `cold`, `clicks`, `input`, `pause`); cold-boot cell `work/scratch/poptick/cell.py`; raw outputs of every table below: `work/gates/tick_*.txt`.
Evidence = disassembly lines of `work/dumps/busy.bin` (`tools/m68dis.py`), raw tool output, or `[INFERENCE]`.

## 0. Result

| item | result |
|---|---|
| world speed | **5.000 turns per real second** (10 VBL per turn at 50 Hz, 12 at 60 Hz) on STE 8 and 16 MHz, Mega STE, TT and Falcon, at 50 and 60 Hz where Hatari allows it (sections 5, 7; Falcon not measured). Unpatched: 3.2-17 (snapshots, 8/16 MHz), 25 (TT), 42 (Falcon). |
| (a) world state by turn | IDENTICAL on 12 matrix runs (3 snapshots x 8/16 MHz x 50/60 Hz, 130 turns each, the whole world region `$21100-$3d7ff` compared at EVERY pass top: 3,000+ compares, 0 differences), 8 slow-machine runs with catch-up passes, 4 command runs, shield countdown, the event of turn `$1000`, 3 runs with the default patch set; 82-262 render-only frames per snapshot equal to the original render; 5 negative controls DIFFER (section 5) |
| (c) responsiveness | pointer: first change 93 ms after a host mouse move (original 82 ms); scroll key held: 18.9 steps/s while the world makes 5.1 turns/s (original 16.7 steps/s at 16.7 turns/s); 28 of 38 steps were made in render-only passes while the turn waited (section 7) |
| default set | HD build = default set (`pop_land_*`, `pop_ptr`, `pop_bgcopy`, `pop_noprot`, `pop_credit`, `pp_bigram_cache`, `pop_fal_ym*`) + the six tick patches: cold boots in section 8 |
| not covered | link games (the tick switches itself off, section 9), real hardware, Falcon at 60 Hz (not reachable in Hatari) |

## 1. How the game paces itself (and what the tick replaces)

`baseline.md`: the loop `$b54e` runs flat out; the only wait is the VBL wait inside the flip `$16f16` (`$16f48 tst.w $16d28.l / beq.b $16f48`), so one pass = one turn = one frame, as fast as the CPU goes. One pass of the loop (`/tmp` dump of `$b54e-$bc12`; sites below are from the same listing):

```
00b632  move.w $3b03c.l,d0   ; pass top (the human player's index); $b6e2 water phase toggle; $b6f4 jsr $14a28 = bg copy = start of the render stage
00b7e6  jsr $16954           ; end of the render stage (terrain $143a2, sprites, manna bar $da90, view marker)
00b7f0  tst.w $3b2b2.l / bne.b $b810   ; paused -> $b810 (people draw loop, no world); $b7f8 tst.w $3b2b4.l (paint mode) same
00b800  jsr $12fc2           ; world, part 1: the object list $3c4ac (flags, animals)
00b806  jsr $db8a            ; world, part 2: people, buildings, effects; $db96 addq.w #1,$3c506.l = THE TURN
00b80c  bra.w $b8ec          ; $b8ec-$b936: shield countdown $3b03e, the event of turn $1000 ($b91c cmpi.w #$1000,$3c506.l / $b932 jsr $133b0)
00b93a  jsr $d4c0            ; shield / selected person display (draws; clears $3c504 when that person is gone)
00b940  jsr $16f16           ; flip: VBL wait, swap $3c510/$3c50c, $ff8201/03
00b946  jsr $200a6 ...       ; keys, keypad scroll ($bb2e), paint keys
00bb7c  ... jsr $11a24 / $d42c / $c420   ; UI: pointer on the land / on a shield / icons; click latches aged at $bbcc-$bbf2
00bbf8  clr.w -(a7) / jsr $1e750  ; command executor (both players' command bytes at $21e4a + $2e*n)
00bc02  move.w #$1,d0 / bne.w $b632
```

The VBL routine `$16d70` (in PP's VBL queue, `$70` = `$d018e`) runs every VBL: button state machine `$16c96`, pointer restore/draw, sound effect start (`$16d98`), IKBD request, flag `$16d28 = 1` (`$16dd6`), counter `$16d2a` `addq.l #1` (`$16dde`). Sound effects are samples played by the timer-A interrupt (`$1717e`), started from `$36d40` by the VBL routine; there is no music or sequencer in play, so there is nothing in the sound that counts passes or VBLs (sound triggers come from the world, per turn).

## 2. What each stage of one pass changes (stage dumps, `busy_castles`, 8 MHz, one pass)

`work/scratch/poptick/stage.py` (restore the snapshot, `b pc = $site && ($3c506).w = N :trace :once :file`, `savebin $0 $100000` at 11 sites of ONE pass, consecutive dumps diffed by `diffs.py`); raw: `work/gates/tick_stage_busy_castles.txt`. Back buffer `$57200`, front `$4f500`.

| stage (site -> next site) | what changed outside the two screen buffers | in the screen buffers |
|---|---|---|
| `$b632` -> `$b6f4` (pass top) | `$3b261` 01 -> 00 (the water phase, `$b6e2-$b6ee`); stack | nothing |
| `$b6f4` -> `$b800` (render stage) | `$3b04b-$3b068` (the sprite list), VBL scratch (`$16d29-$16d2e`, `$2005e`) | 1,298 B |
| `$b800` -> `$b80c` (`$12fc2` + `$db8a`) | people records (`$3b305`, `$3b39f`, `$3b541` ... 20 words: +1 counters), **`$3c507` 21 -> 22 (the turn)** | **438 B = the minimap dots** (x 0..96, y 4..60) |
| `$b80c` -> `$b8ec` -> `$b93a` | nothing | nothing |
| `$b93a` -> `$b940` (`$d4c0`) | stack | 366 B (the shield display) |
| `$b940` -> `$b946` (flip) | `$3c50d-$3c512` (buffer pointers), `$16d29` (flag cleared) | - |
| `$b946` -> `$bbf8` (keys, UI) | stack | - |
| `$bbf8` -> `$bc02` (commands) | stack, TOS scratch | - |

So the render stage writes no world state (only the screen, the sprite list `$3b04a ...`, and the scratch words `$37ef0 $3d58c $37eb6`); the world draws the minimap dots into the back buffer.

## 3. What was counted per pass, and what became of it

| # | item (disassembly) | in the original | now |
|---|---|---|---|
| 1 | turn counter: `$db96 addq.w #$1,$3c506.l` (first instruction after the link of `$db8a`) | +1 per pass | +1 per turn pass (T, S) only: R passes never call `$db8a` (`pop_tick_logic`) |
| 2 | water phase `$3b260`: `$b6e2 move.w $3b260.l,d0` / `$b6e8 seq.b d0` / `and.w #1` / `$b6ee move.w d0,$3b260.l`; read by the world (`$dc98 $e90e $ec16 $ec8e $106ac`) and the render (`$d6c6 $d7ee $d860 $df44 $14700 $14908 $143f0`) | toggles every pass | toggles every turn pass: the tick sends R passes straight to `$b6f4`, over the pass-top part (`pop_tick`); the world compare includes `$3b260` and is identical |
| 3 | pass-top derivations `$21d90 $37ef2 $3b03a` (`$b690-$b6d8`) | per pass | no reader outside `$b6xx` (`--xref`: `$37ef2` is only written, `$21d90` is read in `$b696-$b6d8` and cleared at `$18438`, `$3b03a` is read only at `$b6ca`): dead code, runs with the pass-top part (T, S, P) |
| 4 | object list `$12fc2` (`$12fea addq.w #$1,$c(a0)` per object per pass, animation steps, `$38012` map) | per pass | per turn: skipped in R passes |
| 5 | people, buildings, effects `$db8a`, Armageddon `$3d562`, RNG `$3d56c`, scoring | per pass | per turn |
| 6 | minimap dots: `$166f0` (called from `$db8a` at `$e964 $ec64 $ecdc $106c2` and `$12fc2` at `$13308`) -> `$1672a jsr $167b0` into the back buffer `$3c510` | per pass (drawing inside the logic) | recorded in a turn pass (560-entry list, `pop_tick_dot`), replayed by R passes at the place of the skipped world (`pop_tick_logic`); S passes neither plot nor record |
| 7 | shield countdown `$b8ec-$b912`: `$3b03e` -1 per pass, then `$3c504 = $37ebe`; `$da66` sets it to 10 | per pass | per turn (T, S); R passes jump over it (`$b800` -> `$b93a`). Gate: `--both-poke 3b03e:000a ...` IDENTICAL |
| 8 | event of turn `$1000`: `$b91c cmpi.w #$1000,$3c506.l` / `$b932 jsr $133b0` | at the one pass that has turn `$1000` | R passes keep the turn word, so without the skip it would run on every R pass of that turn; skipped in R. Gate: `--turnjump 4084`: the call is hit once in both runs (`[4096]`) |
| 9 | `$d4c0` shield display (draws; `$d4fe clr.w $3c504.l` when the person is gone) | per pass | every pass kind (also S, where it only keeps `$3c504` right) |
| 10 | render stage `$b6f4-$b7e6` | per pass | T and R passes; S passes skip it (`pop_tick_render`) |
| 11 | flip + VBL wait, keys `$200a6`, keypad scroll `$bb2e`, `$11a24 $d42c $c420` UI | per pass | T and R passes; S passes run none of it (`pop_tick_flip`) |
| 12 | click latches `$3d566` (left) / `$3c514` (right): `$16c96` writes 0 = click waiting (`$16cc4`), `$bbcc-$bbf2` ages them to `(old == 2) ? 2 : 1` after every UI pass | per pass | UI passes of T and R; a FRESH latch is hidden from the UI of an R pass and put back at its end, so a click is taken, and its command written, by the next turn pass (section 7) |
| 13 | command executor `$1e750` (`$bbf8`): player command bytes at `$21e4a + $2e * n`, cleared after running | per pass: a held button writes its command every pass | once per turn (T, S); R passes skip it (`pop_tick_cmd`) and, with the latches hidden, never write one |
| 14 | render flags `$37eb6` (bits 7 and 3, `bset` at `$14682`, `$146d6`; cleared at `$b706`): read by the WORLD at `$df30-$df88` to start sound effects (`$36d40 = $43 + $3b260` / `$46`, cooldown `$36eae`) | the flags of the render of the same pass | T: identical (render then world in one pass); S has no render of its own and sees the flags of the last frame drawn (masked in the gate, section 4) |
| 15 | pointer, buttons, IKBD request, VBL counter | per VBL (VBL routine) | unchanged |
| 16 | sound effects (timer A samples; started from the VBL routine, `$36d40`) | real time | unchanged; the triggers come from the world, now 5 per second |
| 17 | pause `$3b2b2`, paint mode `$3b2b4` | the world and flip run the paused path | kind P: the original pass, clock parked (section 4) |
| 18 | link game: `$1e7e6 move.w $3c524.l,d0 / beq.w $1e974` selects the serial exchange (`$1ff14` send, `$1fe4c` receive through `movea.l #$fffffa01,a1` USART `$2e(a1)`, `$1ff40`, `$1fe78`) | the exchange is the lock-step | kind P while `$3c524 <> 0`: the original pass (not run: no second machine) |

Not found: any other reader of `$16d2a` than the tick (`--xref 16d2a`: `$16dde` the increment, `$1db38`, `$1db50` = a menu/dialog delay), any timer C or `$4ba` use in play.

## 4. The tick

Time base: `$16d2a` in units of 1/300 s: 6 per VBL at 50 Hz, 5 at 60 Hz (`btst #1,$ffff820a.w`, read at every look). TK = 60 units = 0.2 s. ACC = real time not yet simulated (units, clamp 3 TK). The look at every pass top (`pop_tick`, replaces `move.w $3b03c.l,d0`) decides the kind:

| kind | when | what runs |
|---|---|---|
| T | ACC >= TK, nothing else owed | the original pass |
| S | ACC >= TK and another turn still owed after it | pass-top part, world, `$b8ec` block, `$d4c0`, commands: no render, no flip, no keys, no UI, no VBL wait (next pass starts at once) |
| R | ACC < TK (ahead of real time) | render, minimap dots replayed, `$d4c0`, flip, keys, UI with the fresh click latches hidden; no pass-top part, no world, no turn++, no `$b8ec` block, no commands |
| P | `$3b2b2`, `$3b2b4` or `$3c524` set | the original pass; clock parked (`LAST` follows, ACC = 0) |

Resync: more than 40 VBL since the previous look (first look, dialog, load) = one turn, no burst. Catch-up bound: ACC clamp 3 TK = at most four turns in a row without a frame.
Patch sites (all verified against the original bytes by `poppatch.py verify`): `$b632` 6 B, `$b6f4` 6 B, `$b800` 6 B, `$b940` 6 B, `$bbf8` 8 B, `$1672a` 6 B. Relocation: the blobs hold plain game addresses (`$16d2a`, `$3b2b2`, `$3c524`, `$3d566` ...), listed by `verify` and added to by `apply` on TT/Falcon; the data block `$C6000` is outside the program range. Blob map: `$C5000` tick (`$10e`), `$C5200` render, `$C5300` logic, `$C5400` flip, `$C5500` cmd, `$C5600` dot, `$C5800-$C597F` test patches; data `$C6000-$C6E5F` (+ `test_pwalk` `$C6F40`).

### The gate (a): world state by turn (`poptick.py ab SNAP MHZ TURNS`)

Both runs restore the same snapshot and apply a live patch set at `$b806` (`jsr $db8a`) of the same turn t0 (snapshot + 100): base = `test_pwalk` (pointer `$24786/8` and the view `$37eb8/$249ec` as a function of the turn, executed at the pass-top part `$b6e2`, so it runs in T, S, P and in the original but not in R passes; the IKBD packet stores `$2003e` are nopped in both), patched = + the tick set (+ `pop_ptr` etc. with `--defaults`). The world region `$21100-$3d7ff` (116,480 B) is dumped at EVERY pass top (`$b632`) of both runs and compared by turn word: the original has one dump per turn, the tick up to five (T pass, R passes); each must equal the original's dump of its turn. Frames (back buffer at every flip entry `$16f16`, 32,000 B; a breakpoint after the flip clears the stale pointer-restore address `$16f12` in both runs, as `popabtest.py`/`display.md` section 3):

* T frames: the frame of a turn pass equals the original frame of the same turn byte for byte.
* R frames: two R frames of one turn are identical (stability); the minimap rectangle of an R frame (x < 136, y < 68) equals that of the T frame of its turn (the dots replay), except in turns where the world redrew a cell of the CLEAN background minimap (`$c330`, `$c2b8`): the R frame legitimately shows it, the T frame (rendered before the world) not; those turns are counted as excluded and are covered by the render-only compare;
* render-only compare (`--still --render`): the back buffer at `$b800` (render stage done, world not yet run) of an R pass equals the original's at the same turn label byte for byte. The original toggles the water phase at the top of every pass, an R pass does not (by design), so the gate loads `test_rtog_a/b` (toggle the phase in an R pass for the render only); without them 82 of 82 compares differ (control below).

Masks (bytes that follow the number of UI/render passes or an interrupt, not the turns; each was observed by an unmasked run, `poptick.py ab ... --nomask`, `work/gates/tick_ab_nomask.txt`, and none is read by the world apart from `$37eb6`):

| bytes | what |
|---|---|
| `$2478c-$2488b` | the pointer's saved background (VBL routine) |
| `$24990-$249a3` | the sample player's state (timer A, real time) |
| `$36eb0-$36eb7` | the cell under the pointer (UI `$11c18`, `$11c30`; S passes run no UI) |
| `$37ef0-$37ef1` | number of sprites listed by the render |
| `$37eb6` | render flags: read by the world only for the sound trigger (row 14 above); observed different only in S-heavy runs (8 MHz quake) |
| `$3b04a-$3b249` | the sprite list built by the render |
| `$3c50c-$3c513` | the two buffer pointers (every flip swaps them; an R pass flips too) |
| `$3d58c-$3d58d` | cursor-over-icon flags OR-ed by the render |

With `--cmdturn K` the command bytes of player 0 (`$21e4a-$21e51`) are also masked: a command poked in an R pass is pending at the later R pass tops of that turn, and the original has none; its EFFECT (map, manna) is compared after execution.

### Results (a)

`work/gates/tick_ab_matrix.txt`, `tick_ab_spin.txt`, `tick_ab_render.txt`, `tick_ab_cmd.txt`, `tick_ab_misc.txt`, `tick_ab_neg.txt` (one line per run, columns: world tops compared / differ; T frames; R frames; kinds; turns/s of the original and the tick over the captured window, start-up included):

```
matrix (130 turns, no default set, test_pwalk walks pointer and view)
snap / MHz / Hz              result     world tops (differ)  T frames (differ)  R frames (stab pairs / minimap compares)  kinds T R S     base  patched
busy_castles        8 50     IDENTICAL  128 (0)              39 (0)             0                                         40   0  89     3.554  4.939
busy_castles       16 50     IDENTICAL  278 (0)              128 (0)            151 (27 / 104)                            129 151  0     7.509  5.008
busy_quake_volcano  8 50     IDENTICAL  128 (0)              6 (0)              0                                          7   0 122     3.177  4.207
busy_quake_volcano 16 50     IDENTICAL  242 (0)              128 (0)            115 (5 / 71)                              129 115  0     6.747  5.008
genesis_start       8 50     IDENTICAL  211 (0)              128 (0)            84 (0 / 72)                               129  84  0     7.734  5.000
genesis_start      16 50     IDENTICAL  472 (0)              128 (0)            347 (217 / 302)                           129 347  0    16.371  5.023
busy_castles        8 60     IDENTICAL  128 (0)              34 (0)             0                                          35   0  94     3.485  4.946
busy_castles       16 60     IDENTICAL  275 (0)              128 (0)            148 (22 / 104)                            129 148  0     7.435  5.000
busy_quake_volcano  8 60     IDENTICAL  128 (0)              4 (0)              0                                          5   0 124     3.116  4.930
busy_quake_volcano 16 60     IDENTICAL  238 (0)              128 (0)            111 (5 / 65)                              129 111  0     6.684  5.006
genesis_start       8 60     IDENTICAL  206 (0)              128 (0)            79 (0 / 67)                               129  79  0     7.588  5.013
genesis_start      16 60     IDENTICAL  467 (0)              128 (0)            342 (212 / 297)                           129 342  0    16.192  5.026
```

The 8 MHz rows of the busy snapshots are the machine-too-slow case WITHOUT the default set (the original runs 3.2-3.6 turns/s there): all but 5-40 passes are catch-up passes, the world is identical and the rate is 4.2-4.95 (the logic alone costs more than 0.2 s per turn in the volcano scene). With the default set the same scenes need few or no catch-up passes (section 6).

Slow-machine runs (`--spin N`: `test_pwalk` burns N `dbra` iterations = 10 cycles each per turn pass, so a turn costs more than 0.2 s and S passes carry the difference): `tick_ab_spin.txt`, 8 runs IDENTICAL, e.g. `genesis_start 8 MHz 50 Hz +spin 64000`: kinds T 87 R 0 S 42, base 4.241, tick 4.962; 60 Hz: T 82 S 47, 4.159 -> 4.971. The `+spin 90000` / `busy_castles 16 +spin 120000` / `genesis_start 16 +spin 150000` rows are the boundary cases (turn just under or over 0.2 s: R 73 / 138 / 328 passes, S 0).

Commands (`--cmdturn 20`: the bytes `01 20 20` = raise land at vertex (32,32) are poked in an R pass of that turn in the tick run (T/S pass with `--cmdin T`), in the pass top of that turn in the original; the executor runs them at the end of the turn pass in both): `tick_ab_cmd.txt`, 4 runs IDENTICAL (busy_castles 16 MHz, genesis_start 16 and 8 MHz, busy_castles 8 MHz with `--cmdin T`).

Shield countdown, the event of turn `$1000`, default set (`tick_ab_misc.txt`): `--both-poke 3b03e:000a --both-poke 37ebe:0005 --both-poke 3c504:0003` IDENTICAL (60 turns, the countdown runs per turn); `--turnjump 4084` (both runs start at turn 4084, the event at 4096): IDENTICAL, `jsr $133b0` hit once in both (`[4096]`), at 8 MHz / 60 Hz too; `--defaults` (the default set `pop_noprot pop_credit pop_land_mul pop_land_score pop_ptr pop_bgcopy pop_fal_ym*` in both runs): 3 runs IDENTICAL (genesis_start 16 MHz, busy_castles 8 MHz 50 Hz and 16 MHz 60 Hz).

Render-only frames (`tick_ab_render.txt`, 100 turns, `--still --render`): every R pass compared with the original's render of the same turn label: busy_castles 16 MHz 82 compares 0 differ, busy_quake_volcano 16 MHz 64 / 0, genesis_start 8 MHz 64 / 0, genesis_start 16 MHz 262 / 0 (the 8 MHz busy rows have no R passes).

Negative controls (`tick_ab_neg.txt`, all must DIFFER and do):

| control | what it breaks | result |
|---|---|---|
| `--neg` | the tick run does not walk (inputs differ) | world 104 of 104 differ, T frames 58 of 58 |
| `--poke c5306:4e71` | R passes run the world (the `bne.s` of `pop_tick_logic` becomes a `nop`) | world 58 of 58 differ, T frames 30 of 38 differ, the tick rate 7.564 |
| `--poke c560e:60` | the dot recorder never records (`beq.s` -> `bra.s` in `pop_tick_dot`) | R minimap 57 of 57 compares differ, world and T frames still identical |
| `--cmdturn 20 --poke c5506:4e71` | R passes execute commands (`bne.s` of `pop_tick_cmd`) | world 148 of 213 differ, R frames unstable |
| `--turnjump 4084 --poke c5306:4e71` | R passes run the world at the event turn | world 26 of 28 differ |
| `--render --no-rtog` | the render-only compare without the toggle patches | 82 of 82 compares differ (water phase), so the compare resolves it |


## 5. Gate (b): turns per real second

Snapshots, default set in both runs (`poptick.py rate SNAP MHZ 4000 --defaults [--unpatched] [--hz 60]`, 4000 VBL; cycles/VBL prove the refresh), `work/gates/tick_rate.txt`:

| scene | MHz | Hz | original | tick | passes T / R / S |
|---|---|---|---|---|---|
| busy_castles | 8 | 50 | 5.211 | **4.999** | 398 / 25 / 3 |
| busy_castles | 16 | 50 | 10.710 | **4.999** | 400 / 715 / 0 |
| busy_quake_volcano | 8 | 50 | 4.774 | **4.986** | 363 / 6 / 37 |
| busy_quake_volcano | 16 | 50 | 10.235 | **4.999** | 400 / 709 / 0 |
| genesis_start | 8 | 50 | 8.885 | **4.999** | 399 / 397 / 0 |
| genesis_start | 16 | 50 | 17.083 | **4.999** | 400 / 1325 / 0 |
| busy_castles | 8 / 16 | 60 | 5.144 / 10.692 | **4.994 / 4.994** | 330/16/3, 334/591/0 |
| busy_quake_volcano | 8 / 16 | 60 | 4.784 / 10.212 | **4.994 / 4.994** | 305/3/28, 333/584/0 |
| genesis_start | 8 / 16 | 60 | 8.863 / 17.216 | **5.009 / 5.009** | 334/322/0, 333/1097/0 |

## 6. Gate (c): responsiveness and clicks

`tick_input.txt`, `tick_input_defaults.txt`, `tick_clicks.txt`, `tick_pause.txt`. Pointer: first `$24786` change 93 ms after a host move (original 82 ms). Scroll key held 2 s, genesis_start 16 MHz: tick 38 steps (18.9/s, 28 in render-only passes) with 5.10 turns/s; original 34 steps with 16.7 turns/s. busy_castles 8 MHz with the default set: tick 12 steps (6.5/s), original 12 (6.2/s); quake 8 MHz: 11 vs 11. Without the default set at 8 MHz busy (catch-up heavy) scrolling drops to 0.8 steps/s (original 3.4): catch-up passes carry no UI. Clicks: a fresh latch poked during render-only passes reads 1 to the UI and 0 again at the pass end, the next turn pass takes it (latch 0 -> 2); the original takes it in the next pass. Pause: 102 P passes, 0 turns while paused, after unpause 4.98 turns/s with turn gaps 7-12 VBL, no burst.

## 7. Cold boots (default set + tick; `work/gates/tick_cold_*.txt`)

| machine | medium | MHz | Hz | turns/s |
|---|---|---|---|---|
| STE 1 MB TOS 1.62 | HD | 8, 16 | 50, 60 | 4.998, 4.998, 4.999, 4.999 |
| STE 1 MB | floppy | 8, 16 | 50, 60 | 5.015, 4.998, 4.999, 5.015 |
| Mega STE 4 MB TOS 2.06 | HD | 8, 16 | 50, 60 | 4.998, 4.998, 4.982, 4.999 (8 MHz needed catch-up passes) |
| TT 4 MB TOS 3.06 | HD | 32 | 50, 60 | 4.998, 4.999 |
| TT | floppy (text delta $3E48: relocation proven) | 32 | 50, 60 | 5.015, 4.999 |
| Falcon 4 MB TOS 4.04 | HD / floppy | - | - | NOT MEASURED (below) |

## 8. Limits and open items

- **Falcon: no cold boot reached play with the tick build.** HD: the menu was never detected by the scratch cell. Floppy: with the default set alone the Falcon floppy reaches `POPO`; with the tick set the loader's `Pexec(3,"populous.tos")` fails after the DEMO stage (GEMDOS trace) and the game never starts. Cause not found (the same floppy works on STE and TT). Not a proven tick fault, not excluded; first suspect is the larger floppy payload (each patch file is a separate segment padded to a 5120-byte track).
- Link games are not run: the tick is off (kind P) while `$3c524` is set.
- A click is taken by the next turn pass (up to 0.2 s later); two commands issued within one turn lose the first (single slot).
- Catch-up passes carry no UI: a machine too slow for the scene scrolls slowly (section 6).
- Mega STE 8 MHz in Hatari ran slower than STE 8 MHz (28 catch-up passes); cause not investigated.
- Hatari only; real refresh jitter not tested; Falcon 60 Hz not reachable in Hatari.
- Not gated together with other agents' patches (pop_keys, pop_tooltip).

## 9. Reproduce

```
python3 tools/poppatch.py build --hd --out build/PopTiming/hd --only pop_noprot pop_credit pp_bigram_cache pop_land_mul pop_land_score pop_ptr pop_bgcopy pop_fal_ym pop_fal_ym_demo pop_tick pop_tick_render pop_tick_logic pop_tick_flip pop_tick_cmd pop_tick_dot
python3 tools/poptick.py ab busy_castles 16 130 [--hz 60] [--spin N] [--still --render] [--cmdturn 20] [--turnjump 4084] [--defaults] [--nomask]
python3 tools/poptick.py rate busy_castles 8 4000 --defaults [--unpatched] [--hz 60]
python3 tools/poptick.py clicks|input|pause ...
python3 work/scratch/poptick/cell.py ste gemdos build/PopTiming/hd --clocks 8 16 --hz 50 60
```
