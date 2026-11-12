# Populous 2: 60 Hz, and the fixed-rate world tick (6.25 turns per real second)

2026-11-11/12, Pop2Timing. Hatari 2.6.1; snapshots `busy1` and `game_start` (2 MB STE, TOS 1.62, `work/snapshots/`), cold boots of HD builds (STE 2 MB TOS 1.62, Mega STE 4 MB TOS 2.06, TT 4 MB TOS 3.06 `--mmu true`, Falcon 4 MB TOS 4.04).
Patches (all `; default: no`): `pop2_ntsc`, `pop2_ntsc2` (60 Hz), `pop2_tick`, `pop2_tick_render`, `pop2_tick_logic`, `pop2_tick_flip`, `pop2_tick_dot_a`, `pop2_tick_dot_b`, `pop2_tick_snd`, `pop2_tick_anim` (the tick). Test-only: `test_tickspin`.
Tool: `tools/p2tick.py` (gates a/b/c, cold boots, click lifetime, 60 Hz pointer trap, sound steps). Raw outputs of every table below are in `work/gates/*.txt`.
Evidence = disassembly lines of `work/dumps/*.bin` (`tools/m68dis.py`), raw tool output, or `[INFERENCE]`.

## 0. Result

| item | result |
|---|---|
| 60 Hz | **two** protections in the game, both `btst.b #1,$820a.w`: the PAL check at `$1836` ("SORRY PAL MACHINES ONLY") and, hidden in the VBL handler's pointer draw, `$1a6e beq.w $201c` = a loop that zero-fills RAM from address 0 whenever the pointer is lower than y = 184 (PROCEED on the battle sheet is at y = 195). `pop2_ntsc` + `pop2_ntsc2` remove both. Unpatched game at 60 Hz: bus error at `$2022`, `$70` overwritten; patched: runs, and the rendered frame and the world of every turn are byte-identical to 50 Hz (section 1). |
| world speed | **6.25 turns/s on every machine and at 50 and 60 Hz**: 6.247-6.261 over 40-80 emulated seconds on STE 8 and 16 MHz (game_start and busy1), Mega STE 8/16 MHz, TT, Falcon (50 Hz) and with a machine too slow for the scene (busy1 + 0.8 VBL of spin: 5.60 turns/s unpatched, 6.248 patched). Unpatched: 5.6-24 turns/s. (section 5) |
| (a) world state by turn | IDENTICAL on 12 gate runs (busy1, game_start; 8 and 16 MHz; 50 and 60 Hz; 4 of them with catch-up passes), the whole world region compared at every pass top, 0 differences; 2 negative controls differ (section 4) |
| (b) rates | section 5 tables |
| (c) responsiveness | pointer 63-94 ms, scroll steps keep coming in render-only passes while the turn waits (section 6) |
| cold boots | HD build, default set + tick + display patches + 60 Hz fix: STE 2 MB, Mega STE 4 MB, TT 4 MB, Falcon 4 MB all reach play with marker `P2PO`; STE/Mega STE/TT at 50 and 60 Hz (section 7) |

## 1. 60 Hz: why the game dies, and the exact fix

The game is Bullfrog's PAL-only release; it checks the refresh twice.

```
001836  08380001820a   btst.b  #$1, $820a.w          ; shifter sync mode: bit 1 set = 50 Hz
00183c  66000030       bne.w   $186e                 ; 50 Hz: go on
001840  43f90001a9bc   lea.l   $1a9bc.l, a1          ; 60 Hz: "SORRY PAL MACHINES ONLY" ($1856), then
001850  60fe           bra.b   $1850                 ;        loop forever
...
001a5e  044200b8       subi.w  #$b8, d2              ; the VBL handler's pointer draw: pointer y - 184
001a62  6f00000e       ble.w   $1a72                 ; y <= 184: all 16 rows
001a66  9e42           sub.w   d2, d7                ; rows to clip at the bottom edge
001a68  08380001820a   btst.b  #$1, $820a.w
001a6e  670005ac       beq.w   $201c                 ; 60 Hz and the pointer is low:
00201c  91c8           suba.l  a0, a0                ;   zero-fill RAM from address 0 upwards,
00201e  4298           clr.l   (a0)+                 ;   inside the VBL handler, until
002020  60fc           bra.b   $201e                 ;   the bus error
```
`grep` of the linear disassembly of `$1770-$7b380` (`work/dumps/game_start.bin`) for `$820a`/`$ff820a` and `$8260`: the only code references to `$820a` are `$1836` and `$1a68` (other hits are inside text strings); `$8260` is written once (`$1828 clr.b $8260.w`, low resolution). Timer A is the sample player's (`$2a8f0`-`$2a9c8`, rate from `$2b612`), the other MFP/IKBD code does not depend on the refresh. So there is no timer, screen-address or line-count dependence: the "garbage and dies" of the delivery notes is the zero-fill, started by the first pointer position below y = 184 (PROCEED on the battle sheet: ST y = 195).

`tools/p2tick.py pointer60` (busy1, sync register poked to 60 Hz, host pointer moved to the bottom edge), `work/gates/pointer60.txt`:
```
== orig60: sync $00
   pointer x,y = 150,199, turn 16030
   2 s later: turn 16030, vector $70 = $11ac8 (the game's VBL handler is $18fa), $1a6e = $6700
   log: ['WARN : Bus Error writing at address $2, PC=$2022 addr_e3=2022 op_e3=24298']
== fix60: sync $00               (pop2_ntsc + pop2_ntsc2 applied live)
   pointer x,y = 150,199, turn 16052
   2 s later: turn 16077, vector $70 = $18fa (the game's VBL handler is $18fa), $1a6e = $4e71
   log: []
== orig50: sync $fe
   pointer x,y = 150,199, turn 16034
   2 s later: turn 16058, vector $70 = $18fa (the game's VBL handler is $18fa), $1a6e = $6700
   log: []
```
`pop2_ntsc` (`$183c`, `bra.w $186e`) and `pop2_ntsc2` (`$1a6e`, two nops: the 50 Hz clip path at `$1a72` then runs at 60 Hz too).

**The picture at 60 Hz is the picture at 50 Hz.** The unpatched game + the 60 Hz fix + the walk driver, run at 50 and at 60 Hz from the same snapshot; rendered frame (back buffer at the flip, 32,000 B) and world region compared per turn (`p2tick.py hz`, `work/gates/hz_50_vs_60.txt`):
```
busy1 @16 MHz unpatched, 50 Hz vs 60 Hz: IDENTICAL | world per turn 59 compared (0 differ) | rendered frame per turn 59 compared (0 differ) | window 258 VBL at 50 Hz = 5.16 s, 301 VBL at 60 Hz = 5.02 s
game_start @8 MHz unpatched, 50 Hz vs 60 Hz: IDENTICAL | world per turn 59 compared (0 differ) | rendered frame per turn 59 compared (0 differ) | window 272 VBL at 50 Hz = 5.44 s, 310 VBL at 60 Hz = 5.17 s
```
Screenshots (`work/shots/`): `ptr60_fix60.png` (60 Hz, pointer at the bottom edge, running), `tick_ste2mb_60hz.png` (STE, status bar "RGB 60 Hz"), `tick_tt4mb.png` (TT TOS 3.06 cold boot, "32MHz/030(CED)/68882/MMU 4MB TT, TOS 3.06, RGB 60 Hz", game in play), `tick_megaste4mb.png` (Mega STE TOS 2.06 native 60 Hz). Without `pop2_ntsc2` the TT dies the same way (section 7, `tt_ntsc1_only.txt`).

What stays 60 Hz-specific and is NOT fixed (cosmetic, per VBL): the menu/intro/fade timings (`$1bf4` waits, the 17-step palette fade `$2218a`, 0.28 s instead of 0.34 s), the link handshake wait (`$29d52`: 6 VBL). The sound sequencer is fixed (section 3, row 8).

## 2. What one pass of the play loop does (busy1, original code)

`$12524` is the play loop (`jsr $12524` at `$18aa`; one caller); loop top `$1252a`, back-edge `$13340 beq.w $1252a`:
```
012548  jsr $1bf4        ; VBL wait: tst.w $392cc / beq (the flip clears the flag)
01254e  jsr $22f14       ; pacing, click aging, turn++, copies, view clamp   (one caller)
012554  cmpi.w #8,$39766 ; normal map view: render stage $1255e-$12740 (bg copy $1e7b2, $14158 $136ba $13574 $16836, terrain+sprites $1df44, minimap/HUD $1259e-$12740)
012740  jsr $1334a       ; pointer shape from the pointer mode (UI)
012746  tst.w $39796 / 01274c bne.b $1278c                       ; PAUSED: skip the world
01275c  jsr $2309a ; $25652 ; $26644 ; 01276e $27faa ; $1fcce ; $29c7e ; $2a0b2     ; the world logic
01278c  jsr $1bfe        ; flip
012792  jsr $2d4c8       ; an rts
012798  jsr $29226       ; command executor (player slots at $473b0, byte $1(a) through the table at $29300; cleared after; paused: only commands > $66)
01279e  keys ($392f4 table), clicks ($12cca-$12f6e: minimap, scroll pad, command strip, effect rows), hover cell ($12f6e-$13340) ; 013340 beq.w $1252a
```
Stage dumps (`/tmp/p2t/stage.py`: busy1, `b pc = $site && ($3979a).l = N :trace :file`, `savebin $0 $7c000` at 29 sites of ONE pass, consecutive dumps diffed; evidence in this table, script not kept):

| stage (site -> next site) | what changed outside the two screen buffers |
|---|---|
| `$1255e`-`$12584` bg copy, `$14158`, marks, `$136ba`, terrain/sprites `$1df44` | `$20fe9` (scratch inside the sprite code), `$392d1-$392dc` (VBL counters), `$47283` (1 byte: `$4b` of player 2) |
| `$1259e`-`$12740` minimap, HUD | nothing |
| `$12740` `$1334a` | nothing |
| `$1275c` -> `$12762` = `$2309a` people | 168 ranges, 1,058 B: people records `$3b40f-$40xxx`, `$25367`, `$254fe-$2550c` and **320 B of the BACK screen buffer** |
| `$12762` -> `$12768` = `$25652` | `$47285` |
| `$26644 $27faa $1fcce $29c7e $2a0b2` | nothing in busy1 (no effects) |
| flip, `$2d4c8`, `$29226`, keys | flip variables; nothing |

The 320 B are the minimap dots: `$24244`-`$24296` plots one pixel per person into the back buffer (`$24290 movea.l $392e0.l,a0` / `$24296 jsr $20058.l`; d0/d1 from the object's x/y, d2 from the table `$309d8` + the turn parity `$3979c & 1`), and `$2793c`/`$27942` does the same for effect objects. The logic also redraws minimap cells of the CLEAN background (`$1fe52 jsr $1f6e0` -> `$1f74c jsr $20058`, seen at turn 16141 in `$20058`-caller traces). The render stage writes no world state; the only write of the draw code into object records is `$20c50 move.w d2,$a(a3)` (kind `$14` animation step, section 3 row 9) and the `$4b(player)` visibility bits (`bset` at `$2081a $20914 $20aa0`, read by the UI at `$13170 $1f7ca $1f7d2`). `$22f14` holds the turn (`$22f9c addi.l #1,d0` / `$22fa2 move.l d0,$3979a.l`, skipped while paused).

`$20058` callers in one patched turn at 16 MHz (T pass: `ret=$2429c` x 127; the R passes' replay from `$82282` x 127; the render stage's own 21 calls `$13726` x 9 + `$1ff8a` x 12 in every pass).

## 3. What was counted per pass, and what became of it

| # | item (disassembly) | in the original | now |
|---|---|---|---|
| 1 | turn counter `$3979a`: `$22f7e move.l $3979a,d0` ... `$22f9c addi.l #1,d0` / `$22fa2 move.l d0,$3979a.l` | +1 per pass | +1 per turn pass (T, S) only (`pop2_tick`) |
| 2 | world logic `$2309a $25652 $26644 $27faa $1fcce $29c7e $2a0b2` (`$1275c`-`$12786`) | once per pass | once per turn: skipped in R passes (`pop2_tick_logic`) |
| 3 | command executor `$29226` (`$12798`) | once per pass: a held mouse button / key writes its command again every pass, so at 16 MHz the player would act twice per turn [INFERENCE: read from `$12cca`-`$12f6e` and `$29226`, not run with a held button] | once per turn (T, S passes; R passes skip it: the command waits in its slot, the UI writes it again) (`pop2_tick_flip`) |
| 4 | **click age** `$22f84 cmp.l $3940a,d0` / `ble.b $22f9c` / `clr.w $39402` / `clr.w $39404`; stamps `$1980`, `$19dc` `move.l $3979a.l,$3940a.l` | compares TURNS: with R passes (no turn++) an unhandled click would live two whole turns, with S passes (turns with no UI) it would be cleared before any UI pass saw it | aged per UI pass (T and R), never in S passes: `pop2_tick` reads the stamp, re-arms it with a sentinel (`$7fffffff`, so `$22f84` never clears), a stamp that changed = a fresh click (survives this pass), unchanged with a latch set = seen by a whole pass: cleared. Measured: `work/gates/clicks.txt` (below) |
| 5 | pointer-at-(0,0) hold: `$22f14 move.w $393fa,d0 / add.w $393fc,d0 / bne $22f2e`, `$22f22 cmpi.l #8,$392d4 / ble.b $22f14` | no pass shorter than 9 VBL (0.18 s at 50 Hz) while the pointer is in the top-left corner | the same in real time: HOLD = 54 units of 1/300 s (9 VBL at 50 Hz, 11 at 60 Hz); never delays an S pass, so the world keeps its 6.25 turns/s |
| 6 | 3-turn palette fade `$22f3c`-`$22f70` (`$22fc4 = turn + 3`, then `jsr $2218a`: 17 steps, one per VBL, blocking) | per turn | unchanged (it runs inside T/S passes through `$22f2e`) |
| 7 | copies `$22fa8 move.w $47386,$47148` / `$22fb2 move.w $47388,$47282` | per pass | per turn (T, S) |
| 8 | **sound** `$191e jsr $2b29a` (VBL handler, while `$2cade` is set): sequencer step per VBL | 50 steps/s at 50 Hz, 60 at 60 Hz | `pop2_tick_snd`: 1/300 s units (+6 per VBL at 50 Hz, +5 at 60 Hz, one step per 6): 50.00 steps/s at both (below). Timer A sample playback is not tied to the VBL. |
| 9 | **animation by drawing**: `$20c3e addq.w #4,d2` ... `$20c50 move.w d2,$a(a3)` (draw routine of kind `$14`, entry `$20c00`) | one step per pass | R passes show the stored frame without stepping (`pop2_tick_anim`); [INFERENCE] no kind-`$14` object occurs in busy1/game_start (kinds `2 4 18`, third list `22`), and a record forced to kind `$14` with owner 1 stays on frame `$a88` (the table at `$32902` wraps at once), so the synthetic test (`ab --both-poke 400ee:14 --both-poke 400fa:01`) exercises the R path (IDENTICAL) but cannot show a difference |
| 10 | **minimap** dots plotted by the logic (`$24296`, `$27942`) | once per pass (drawn inside the world logic) | recorded in turn passes (`pop2_tick_dot_a/b`, 900-entry list), replayed by R passes at the place of the skipped logic; S passes neither plot nor record |
| 11 | turn-based animations: `$13470`/`$1346a`/`$134be`/`$134d2` (pointer shape `$3979c & $18`: a phase per 8 turns), `$1317c`, `$13846`, `$20af8` (`$3979c & 1`), `$24244` (dot colour parity), `$1fdb6` (`and.w $30e86`) | per turn already | per turn (now 6.25 Hz on every machine) |
| 12 | turn-scheduled logic: land score stagger `$25172`-`$25182` (`(index & 3) == (turn & 3)`), `$29c90 cmp.w $3979c,d0` (message queue `$39638`), `$25a32 cmpi.l #$fa,$3979a`, `$24a56`, `$2760c` | per turn | per turn |
| 13 | VBL counters: `$392d8` (+1 per VBL, `$1910`), `$392d4` (VBLs since the pass top: `$22f22`, link wait `$29d52`), `$392d0` (free-running word, RNG seed `$148f4`) | per VBL | unchanged; `$392d8` is the tick's time base |

Not found per pass: any other `$392d4`/`$392d8` reader in the play loop. The IKBD poll (`$1a0a move.b #$d,$fc02.w`) and the pointer draw are per VBL (60/s at 60 Hz).

Click lifetime, `work/gates/clicks.txt` (both latches and the stamp poked at the top of pass j; latch value after the pass-top look, per pass):
```
orig busy1 16 MHz:      T j: 1 1   T j+1: 0 0
patched busy1 16 MHz:   R j: 1 1   R j+1: 0 0                       (same lifetime: seen by one pass, cleared at the next UI pass)
patched busy1 8 MHz, ACC forced to 140: S 1 1 | S 1 1 | S 1 1 | S 1 1 | T 1 1 | T 0 0     (four catch-up passes without UI keep the click; the T pass sees it)
```

The (0,0) hold, `p2tick.py hold game_start 16` (`work/gates/hold.txt`, host pointer homed = game pointer (0,0), 3000 VBL):
```
50 Hz orig    : world turns 334 in 60.0 s = 5.565/s  (one pass per 9 VBL)
50 Hz patched : world turns 375 in 60.0 s = 6.248/s; UI passes (T+R) one per 9.01 VBL; catch-up passes S 42
60 Hz orig    : world turns 333 in 50.0 s = 6.658/s  (9 VBL = 0.15 s)
60 Hz patched : world turns 312 in 50.0 s = 6.238/s; UI passes one per 10.99 VBL (= 0.183 s, the real-time hold); catch-up passes S 39
```

Sound steps per VBL, `p2tick.py snd` (busy1, `$2b29a` entry hits):
```
50 Hz orig   : 5227 sequencer steps in 5227 VBL = 1.0000 per VBL = 50.00 steps per second
50 Hz patched: 5518 sequencer steps in 5518 VBL = 1.0000 per VBL = 50.00 steps per second
60 Hz orig   : 6646 sequencer steps in 6646 VBL = 1.0000 per VBL = 60.00 steps per second
60 Hz patched: 5581 sequencer steps in 6697 VBL = 0.8334 per VBL = 50.00 steps per second
```

## 4. The tick

Time base: the game's VBL counter `$392d8` in units of 1/300 s: 6 per VBL at 50 Hz, 5 at 60 Hz (`btst #1,$ffff820a.w`, read at every look). Not timer C: `$114` is pointed at an `rte` (`$1d60 move.l #$1de0,$114.l`, all MFP vectors) and IERB = `$40`, `$4ba` did not move (`hz200.py`: `4ba 17667 17667`, 251 VBL).
TK = 48 units = 0.16 s. ACC = real time not yet simulated (units; clamp 3 TK). Every pass starts with the look in `pop2_tick` (it replaces the first 12 bytes of `$22f14`):

| kind | when | what runs |
|---|---|---|
| T | ACC >= TK, nothing else owed | the original pass; falls into the game's own code at `$22f2e` (turn++, fade, copies, clamp) |
| S | ACC >= TK and another turn still owed after it | turn + logic + commands; no render, no UI, no flip (`pop2_tick_render` jumps `$12554` -> `$12746`, `pop2_tick_flip` jumps `$1278c` -> `$29226` -> `$1252a`); no VBL wait is needed (the flip clears `$392cc`, without a flip the next pass starts at once) |
| R | ACC < TK (ahead of real time) | render + UI + flip; no turn++, no logic, no commands, no copies; minimap dots replayed |
| P | `$39796` set (paused) | the original pass, clock parked (the game's pause path handles it; R passes must not take it: `$292e8` drops commands <= `$66` while paused, which would swallow the unpause) |

Resync: more than 40 VBL since the last look (first look, a load, a requester) = one turn, no burst. Catch-up bound: at most four turns in a row without a frame (ACC clamp 3 TK). Patch sites (`pop2patch.py build` output): `$22f14` 12 B, `$12554` 8 B, `$12746` 8 B, `$1278c` 18 B (flip + `jsr $2d4c8` + `jsr $29226`), `$24296` 6 B, `$27942` 6 B, `$191e` 6 B, `$20c3e` 22 B. Blobs `$82000`-`$8260x`, data `PB+$2800` = `$82800-$83FFF` (inside the zero-filled payload image; `$8A000-$8BFFF` as first allocated is inside `pop2_spr`'s `$88200-$8FFFF`: the build says `image overlap: $88200-$90000 vs $8a000-$8c000`).

### Gate (a): world state by turn (`p2tick.py ab SNAP MHZ TURNS [--hz 60] [--spin N]`)

Both runs restore the same snapshot and apply a live patch set at the flip of the same turn (`$1c04`, turn = snapshot + 100): base = walk driver (`test_walk*`: pointer and view are a function of the turn; the tick's T/S passes still run `$22fa2`), patched = + the tick set (+ `pop2_ntsc*` at 60 Hz in BOTH). The world region `$39600-$473ff` (56,832 B: map, people, effects, players, RNG `$47382`, view, click state) is dumped at EVERY pass top (`$1254e`) of both runs and compared by turn: the unpatched game has one dump per turn, the patched game up to five (T pass, R passes); each must equal the unpatched dump of its turn. Rendered frames (back buffer at every flip) likewise: the T pass of turn k against the unpatched frame k; R frames: two R frames of one turn must be equal, and their minimap rectangle equal to the T frame's.
Masks (UI scratch that follows the number of UI passes, not turns): `$3962e-$3962f` (hover flag copied from `$3e7a4` at `$125aa`), `$3e7a2-$3e7a9` (hover cell computed by the UI stage, cleared at `$12f6e`), `$47149` and `$47283` (`$4b(player)` visibility bits, set by the sprite code). Frames of a turn pass that directly follows catch-up passes are not compared (the hover highlight comes from the previous pass's UI, which an S pass skipped). A turn where the logic redrew a minimap cell of the clean background (`$1f74c`) is excluded from the R-vs-T minimap compare (the R frame legitimately shows the new cell).
Full output `work/gates/ab_matrix.txt`, `ab_spin.txt` (the two `--hog` lines of `ab_matrix.txt` ran with the hog count at 0, i.e. plain runs: they are the `busy1 8 MHz` rows below; `test_hog` was replaced by `test_tickspin`):
```
busy1 @8 MHz 50 Hz: IDENTICAL | world at pass tops: 134 compared (0 differ) over 131 turns | T frames 111 compared (0 differ; 9 excluded) | R frames: 5 | pass kinds T 121 R 5 S 9 | turns/s base 6.190 patched 6.232
busy1 @16 MHz 50 Hz: IDENTICAL | world 325 compared (0 differ) over 131 turns, max 3 tops/turn | T frames 129 (0 differ) | R frames 198 (72 stability pairs, 0 unstable; 192 minimap compares, 0 differ) | T 130 R 198 S 0 | turns/s base 11.733 patched 6.274
game_start @8 MHz 50 Hz: IDENTICAL | world 239 compared (0 differ) | T frames 129 (0 differ) | R frames 111 (107 minimap compares, 0 differ) | T 130 R 111 S 0 | base 10.998 patched 6.262
game_start @16 MHz 50 Hz: IDENTICAL | world 507 compared (0 differ), max 4 tops/turn | T frames 129 (0 differ) | R frames 381 (250 stability pairs, 370 minimap compares, 0 differ) | base 24.074 patched 6.286
busy1 @16 MHz 60 Hz: IDENTICAL | world 307 compared (0 differ) | T frames 129 (0 differ) | R frames 180 (0 differ) | base 12.093 patched 6.265
busy1 @8 MHz 60 Hz: IDENTICAL | world 133 compared (0 differ) | T frames 111 (0 differ; 9 excluded) | T 121 R 5 S 9 | base 6.142 patched 6.240
game_start @8 MHz 60 Hz: IDENTICAL | world 248 compared (0 differ) | T frames 129 (0 differ) | R 120 | base 11.573 patched 6.270
game_start @16 MHz 60 Hz: IDENTICAL | world 504 compared (0 differ), max 5 tops/turn | T frames 129 (0 differ) | R 379 (247 stability pairs, 367 minimap compares, 0 differ) | base 20.000 patched 6.280
-- slow machine (every pass +12800 dbra = 0.8 VBL at 8 MHz; game_start +45000), S passes carry the difference --
busy1 @8 MHz 50 Hz +spin 12800: IDENTICAL | world 129 compared (0 differ) | T frames 93 (0 differ; 18 excluded) | pass kinds T 112 R 0 S 18 | turns/s base 5.768 patched 6.226
busy1 @8 MHz 60 Hz +spin 12800: IDENTICAL | world 129 compared (0 differ) | T frames 87 (0 differ; 21 excluded) | T 109 R 0 S 21 | base 5.681 patched 6.210
game_start @8 MHz 50 Hz +spin 45000: IDENTICAL | world 136 compared (0 differ) | T 130 R 7 S 0 | base 6.533 patched 6.214
game_start @8 MHz 60 Hz +spin 45000: IDENTICAL | world 132 compared (0 differ) | T 130 R 4 S 0 | base 6.436 patched 6.245
-- negative controls (must DIFFER) --
--neg (the patched run does not walk):          DIFFER | world 134 compared (134 differ): $3e79f 000017 / 07001b | T frames 59 differ
--poke 82246:4e71 (R passes run the logic):     DIFFER | world 110 compared (110 differ): 210 ranges (people records) | T frames 59 differ | R minimap 46 of 49 differ
```
(The turns/s printed here are over 60-130 captured turns including the start-up; section 5 has the long windows.)
Earlier mismatches found and resolved by this gate: the hover flag `$3962f` (UI scratch, now masked: it showed 00 / 8c after the R passes ran the UI one pass more per turn), `$47283` and `$3e7a2` after catch-up passes (same class), and R-frame minimap differences of 5 B at turn 16141 = the minimap cell redraw in the logic (the `$20058` caller trace shows 4 calls from `$1f752` in that turn).
`test_hog` (blitter burst) cannot be used here: it makes the ACIA lose bytes and the game takes `Address Error reading at address $296f, PC=$1934` (the button byte `$2023` indexes the jump table at `$1936`); `pop2_clamp` exists for that. `test_tickspin` burns cycles without touching interrupts or the bus.

## 5. Gate (b): turns per real second

Emulated seconds = VBL / refresh; cycles per VBL prove the refresh (8 MHz / 50 = 160,000; / 60 = 133,333). `p2tick.py rate` (snapshot restored, live set applied at the flip, 80 emulated seconds), `work/gates/rate_ste_50.txt`, `rate_ste_60.txt`, `ab_spin.txt`:

| scene | MHz | Hz | unpatched turns/s | patched turns/s | patched passes (T / R / S) |
|---|---|---|---|---|---|
| game_start | 8 | 50 | 9.448 | **6.248** | 500 / 285 / 0 |
| game_start | 8 | 60 | 8.848 | **6.249** | 500 / 245 / 0 |
| game_start | 16 | 50 | 16.658 | **6.248** | 500 / 935 / 0 |
| game_start | 16 | 60 | 18.834 | **6.249** | 500 / 1100 / 0 |
| busy1 | 8 | 50 | 6.061 | **6.261** | 462 / 0 / 39 |
| busy1 | 8 | 60 | 5.974 | **6.249** | 452 / 0 / 48 |
| busy1 | 16 | 50 | 11.010 | **6.248** | 500 / 662 / 0 |
| busy1 | 16 | 60 | 11.135 | **6.249** | 500 / 766 / 0 |
| busy1 + 0.8 VBL spin (slow machine) | 8 | 50 | 5.599 | **6.248** | 388 / 0 / 112 |
| busy1 + 0.8 VBL spin | 8 | 60 | - | **6.249** | 372 / 0 / 128 |
| game_start + 2.8 VBL spin | 8 | 50 | 5.799 | **6.248** | 423 / 0 / 77 |

(busy1 at 8 MHz, 50 Hz: 501 turns in 80 s: +0.2 % = the catch-up debt of the restored snapshot; the original there runs 6.06 turns/s, 3 % under the target, so catch-up passes make it up.)

Cold boots (`p2tick.py cold`, HD build `build/tick_hd` = pop2_credit + display patches `pop2_spr pop2_spr16 pop2_ptr_a pop2_ptr_b pop2_clamp` + `pop2_ntsc pop2_ntsc2` + the tick set; boot to the first battle with `boot_to_game`, then 40 emulated seconds, `work/gates/cold_*.txt`):

| machine | boot | MHz | Hz (cycles/VBL) | turns/s | passes T / R |
|---|---|---|---|---|---|
| STE 2 MB, TOS 1.62 | 50 Hz | 8 | 50 (160,256) | **6.247** | 250 / 188 |
| | | 16 | 50 (320,406) | **6.247** | 250 / 625 |
| | poke `$ff820a` = 0 | 8 | 60 (133,576) | **6.247** | 250 / 180 |
| | | 16 | 60 (267,167) | **6.247** | 250 / 550 |
| Mega STE 4 MB, TOS 2.06 | 60 Hz native | 8 | 60 (133,552) | **6.247** | 250 / 31 |
| | | 16 | 60 (267,167) | **6.247** | 250 / 350 |
| | poke `$ff820a` = 2 | 8 | 50 (160,203) | **6.247** | 250 / 41 |
| | | 16 | 50 (320,435) | **6.247** | 250 / 334 |
| TT 4 MB, TOS 3.06, `--mmu true` | 60 Hz native (`$ff820a` = `$01`) | 32 | 60 (534,334) | **6.247** | 250 / 950 |
| | poke `$ff820a` = 2 | 32 | 50 (640,724) | **6.247** | 250 / 1500 |
| Falcon 4 MB, TOS 4.04 | 50 Hz (`$ff820a` = `$02`) | 16 | 50 (320,356) | **6.247** | 250 / 625 |

Falcon at 60 Hz: **not reachable in Hatari**. Poking `$ff820a` = 0 changes the register but not the VBL (317,886 cycles/VBL = 50.33 Hz; the tick, which reads the register, then runs 5.2 turns/s of real time: that row of `cold_falcon.txt` is NOT a 60 Hz measurement, `p2tick.py` now prints "*** NOT 60 Hz ***" for it); `--language us --layout us` and `--monitor vga` both boot at 50 Hz (`$ff820a` = `$02`, 320,366 and 320,431 cycles/VBL: `cold_falcon_us.txt`, `cold_falcon_vga.txt`). On real hardware the register and the refresh agree [INFERENCE].

## 6. Gate (c): responsiveness (`p2tick.py input`, real-time mode, `work/gates/input.txt`)

The pointer is drawn by the VBL handler (`$18fa`-`$1b4e`), untouched by the tick; scroll keys act once per pass that runs the UI (R and T passes), as in the original.
```
orig    16 MHz: pointer first $393fa change 83 ms after the move | scroll Right held 2 s: 20 view steps, 9.7 steps/s, world turns during the steps 9.69/s
patched 16 MHz: pointer first change 63 ms                       | 22 view steps, 10.8 steps/s, world turns 6.19/s; 9 of the steps were made in render-only passes (turn waiting)
orig     8 MHz: pointer 93 ms | 11 steps, 5.3 steps/s, turns 5.26/s
patched  8 MHz: pointer 94 ms |  9 steps, 4.6 steps/s, turns 6.32/s (no R passes at this clock; S passes carry no UI)
```
The pass timeline at 16 MHz (`ab` pass-kind log, busy1): turn 16123: T at VBL 141126, R 141128, R 141130; turn 16124: T 141134, R 141136, R 141138 ...: a frame every 2-3 VBL while the world moves every 8. 1 step per pass is the original's scroll rate per pass; the world no longer follows it.

## 7. Cold boots of the acceptance build (HD, `build/tick_hd`)

All four reach play with `$7fff8` = `P2PO` and `$22f14` = `4ef900082000` (the tick's jump): `work/gates/cold_ste.txt`, `cold_megaste.txt`, `cold_tt.txt`, `cold_falcon.txt`; screenshots `work/shots/tick_ste2mb.png`, `tick_ste2mb_60hz.png`, `tick_megaste4mb.png`, `tick_megaste4mb_50hz.png`, `tick_tt4mb.png` (60 Hz), `tick_tt4mb_50hz.png`, `tick_falcon4mb.png`. Without `pop2_ntsc2` (`work/gates/tt_ntsc1_only.txt`, `work/shots/tt_ntsc1_only.png`): TT 4 MB TOS 3.06 cold boot of a build with `pop2_credit pop2_ntsc` only: the PAL check is passed, `boot_to_game` = False, `$ff820a` high byte = `$01` (60 Hz), turn 0, and the screenshot is the garbage screen with the two TOS bombs, i.e. the delivery notes' "garbage and bus errors at `$201e`" (the zero-fill started by PROCEED at y = 195, section 1).

## 8. Limits, open items, [INFERENCE]

- Hatari only. 60 Hz on Falcon not reachable (section 5). Real-hardware refresh jitter: the time base is the VBL count, so it is exactly as accurate as the display refresh; a 50.0 Hz PAL display gives 6.25 turns/s, a 60 Hz one the same through the 5-unit step [INFERENCE for real hardware].
- The R pass leaves the player's command in its slot until the next turn pass; two different commands issued between two turn passes (< 0.16 s) lose the first (single slot `$1(a)`). The original at 16 MHz would have run both [INFERENCE from `$29226`].
- Link games (`$29cd0`, serial/MIDI) were not run; the exchange sits in the command executor and the 6-VBL wait `$29d52`, so it should follow the turn [INFERENCE].
- The hover highlight can lag by the UI passes an S burst skips (cosmetic; the gate excludes those frames).
- `pop2_tick_anim`: untested against a real kind-`$14` object (none exists in the snapshots).
- The floppy build and the other default-set interaction (`pop2_save_*`) were not run with the tick; the tick patches only add blobs in the image and 8 sites, and the HD and floppy payloads are built by the same code path (`patches/README.md`).
- Menus, intro, fades and the link handshake stay on VBL time (20 % shorter at 60 Hz).

## 9. Reproduce

```
python3 tools/pop2patch.py verify
python3 tools/pop2patch.py build --hd --out build/tick_hd --only pop2_credit pop2_spr pop2_spr16 pop2_ptr_a pop2_ptr_b pop2_clamp pop2_ntsc pop2_ntsc2 pop2_tick pop2_tick_render pop2_tick_logic pop2_tick_flip pop2_tick_dot_a pop2_tick_dot_b pop2_tick_snd pop2_tick_anim
python3 tools/p2tick.py pointer60                                   # the 60 Hz trap, with and without pop2_ntsc2
python3 tools/p2tick.py hz busy1 16 60                              # 60 Hz picture == 50 Hz picture
python3 tools/p2tick.py ab busy1 16 130 [--hz 60] [--spin 12800]    # (a)  (negative controls: --neg, --poke 82246:4e71)
python3 tools/p2tick.py rate busy1 8 4000 [--unpatched] [--hz 60 --ntsc]   # (b)
python3 tools/p2tick.py cold --machine tt --tos 3.06 --mem 4096 --tag tt4mb --hz 60 50 --clocks 0
python3 tools/p2tick.py input busy1 16 [--unpatched]                # (c)
python3 tools/p2tick.py clicks busy1 16 [--unpatched] [--force-s]
python3 tools/p2tick.py snd
```
