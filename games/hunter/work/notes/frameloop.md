# Hunter frame loop (HunterBench)

Evidence: `work/dumps/ram_foot_stand.bin` (disassembled with `tools/m68dis.py`), `Hunter.site_trace` (breakpoints + `e CycleCounter`),
`hi cpu` instruction history captured at `$5f6a` (the last 400 instructions end in `$2594 pea $253e(pc)`, `$25a4 .. rts`, `$253e`).
`a5 = $806` holds the game variables (`$93(a5)` = `$899`, `$144(a5)` = `$94a`, ...).

## 1. The loop (continuation style: `pea $253e(pc)` then dispatch at `$25a4`, whose `rts` re-enters `$253e`)
```
00253e: bset.b #7,$93(a5)            ; "3D loop active" ($899 bit 7, the RAM marker)
002544: bsr.w  $5f6a                 ; frame pacing + FLIP (see 2)
002548: bsr.w  $6000                 ; camera term: divs.w #$2b00 -> $1544(a5)  (horizon row)
00254c: btst #5,$93(a5) / bsr $2606  ; (rare) wait for a flag
002558: bsr.w  $7db0
00255c: bsr.w  $269c                 ; per-frame logic ($269c..)
002560: bclr #7,$9f(a5) ... bra $34ca (other mode)
002572: bsr.w  $372c
002576: jsr    $c84a                 ; dither fill of the ground/water rows (2.3-3.4 %)
00257c: bsr.w  $41d8
002580: bsr.w  $3990                 ; 3D RENDER (74-88 % of the frame)
002584: btst #2,$93(a5) / bsr $406a  ; (conditional)
002590: bsr.w  $96f6
002594: pea $253e(pc) ; 00259a bclr #1,$93(a5) / bne $4764 ; fall into $25a4: event dispatcher on $a1(a5) bits, rts -> $253e
```
Order of calls and mean cycle cost between the sites (8 MHz; 20-35 frames each; trace sites `$253e,$2544,$2548,$2558,$255c,$2572,$2576,$257c,$2580,$2584,$2590,$2594`):
| stage | foot_stand | foot_walk | car_stand | car_drive | car_turn |
|---|---:|---:|---:|---:|---:|
| $5f6a frame-pace wait + flip (+VBL spin) | 43,882 (2.5%) | 96,438 (9.5%) | 72,786 (5.0%) | 71,833 (6.4%) | 88,121 (7.4%) |
| $6000 | 276 (0.0%) | 276 (0.0%) | 276 (0.0%) | 276 (0.0%) | 275 (0.0%) |
| $7db0 | 2,592 (0.1%) | 2,592 (0.3%) | 2,592 (0.2%) | 2,592 (0.2%) | 2,592 (0.2%) |
| $269c | 19,156 (1.1%) | 18,563 (1.8%) | 16,500 (1.1%) | 20,054 (1.8%) | 19,568 (1.6%) |
| $372c | 2,027 (0.1%) | 2,021 (0.2%) | 1,844 (0.1%) | 2,278 (0.2%) | 2,141 (0.2%) |
| $c84a dither/ground fill | 60,324 (3.4%) | 60,383 (5.9%) | 60,483 (4.2%) | 59,799 (5.3%) | 59,828 (5.0%) |
| $41d8 | 25,769 (1.5%) | 24,365 (2.4%) | 22,923 (1.6%) | 22,670 (2.0%) | 22,731 (1.9%) |
| $3990 3D RENDER | 1,556,050 (88.3%) | 753,816 (74.2%) | 1,211,539 (84.0%) | 888,680 (79.2%) | 936,854 (78.7%) |
| $406a (cond.) | 28 (0.0%) | 28 (0.0%) | 28 (0.0%) | 28 (0.0%) | 28 (0.0%) |
| $96f6 | 52,595 (3.0%) | 57,054 (5.6%) | 53,609 (3.7%) | 53,520 (4.8%) | 58,471 (4.9%) |
| **frame total (cycles)** | 1,762,721 (21 frames) | 1,015,560 (34 frames) | 1,442,603 (24 frames) | 1,121,753 (35 frames) | 1,190,632 (30 frames) |
`$3990` (render) contains the template copy `$c91a`(a loop over `$3a(a5)+1` rows x 5x32 B), the cell/terrain walk `$3ada`, vertex transform `$5452/$54f4`, projection `$5268`, edge setup `$7450`, scan conversion `$7518`, span fills `$7af0`.
Logic vs render: logic = all other rows = 12 % (stand) to 26 % (walk) of the frame; render 74-88 %.
The loop is generic over game modes (`$a1(a5)` event bits dispatch to `$a204/$9f8a/$3cb8/$8bf8/$a456/$d182`), `$481c` is the same kind of loop for another mode (never hit while walking/driving).

## 2. Flip and buffers
- `$5f6a`: `tst.b $95(a5) / bpl $5fc2`. Normal path `$5fc2`: `bsr $5fd2` (flip) / `bsr $aaa2` (VBL lock) / `bra $5fa4` (`move.w $1aa(a5),$1ac(a5); clr.w $1aa(a5)`; `subq.w #1,$198(a5)` etc.). The other path (bit 7 of `$95` set: scripted/intro) waits `cmp.w $1a8(a5),d0` against a schedule table `$7f5c`+`$cc(a5)` (`$5f7e..$5f82` spin) and `jsr $2640` when the table ends.
- `$5fd2`: `d0 = ($7f6c) = $23000`, `d1 = ($7f74) = $2ad00`; `bchg #2,$8f(a5)` swaps them, stores `$144(a5)` (draw buffer) and `$148(a5)` (display buffer), writes `$ff8203` (`move.b d1,$203(a6)`, mid byte, at `$5fee`) and `$ff8201` (`$5ff4`). **Double buffer**, 32,000-byte pages at `$23000` and `$2AD00` (the 3D window is 140 rows: `$8c`, offset `$5780` = 22,400 B at `$1a2(a5)`; HUD rows below are drawn separately). `$14c(a5)` = `$3682c` third pointer (`$7f7c`, other use).
- Flip is VBL-locked: `$aaa2` spins until the VBL-decremented byte `$1a6(a5)` goes negative (reload `$1a7`; 11 in the cold-boot dump, 0 in snapshots), then `bset #3,$8f(a5) / bne` spins until the VBL handler `bclr #3,$8f(a5)` (`$c616`). So frames end on VBL boundaries (VBL/frame distribution at 8 MHz stand: 11 x 20 of 20; at 16 MHz 6 x 40 of 40).
- Frames per second = 50 / (VBLs per frame); the idle spin (`$aab4`: 2-6 % of cycles) is the slack until the next VBL.

## 3. VBL handler `$c5f0` (vector `$70`; also `$68`/`$120` = `$aa6e`)
`ori #$700,sr`, saves d0-d7/a0-a4, then: `$c63a` (LFSR `$c6a4`; if 3D loop active: `$1a8++`, `$1aa++`, joystick state `$d1(a5) -> $d0`, `$cf`; `$c6b4`; `$699c` per-VBL timers; `jsr $355a` (camera pitch/step easing `$1530/$1536(a5)`, `$26a` direction decode)), `moveq #$16,d0 / bsr $afbe` (IKBD "interrogate joysticks": `$afc4` waits TDRE then `move.w #$c8,d0 / nop / dbra` = ~2,800-cycle delay, 2.4 % of all cycles), timers `$ea,$1a6`, `bsr $c628` (sound driver tick through `$7f44` -> `$10fb2`: `jmp $40(a0)`), `bclr #3,$8f(a5)`, `bclr #7,$8f(a5)`, rte.

## 4. Input
- IKBD/ACIA interrupt (MFP GPIP4, vector `$118` = `$afde`): loop `move.b $fffc00,d2 / bpl / btst #0 / beq`, on RDRF `jmp $1ae` = PP's patch hook (copy of START's `$f87a`): `move.b $fc02.w,d0 / cmp.b #$c3,d0` (F9 break code = Gamex menu, saves the machine state and `jmp $ffd20`), anything else `jmp $aff4 -> bsr $b01e` (the game's key/mouse/joystick packet decoder), then the loop waits for GPIP4 to go high (`btst #4,$fa01(a6)`).
- Joystick: polled by the VBL handler with IKBD command `$16`; result packet decoded into `$d1(a5)` / `$d0`. On foot the stick is screen-relative (N = +Z, W = -X); in vehicles N accelerates, W/E turn (manual).
- Mouse: IKBD relative packets decoded by `$b01e` [INFERENCE: camera yaw/pitch and the HUD pointer]; the game pointer is a software sprite.
- Keyboard events sent with `hatari-event keypress` (press+release in the same millisecond) leave the ISR looping at `$afe6` (ACIA IRQ line stays low); use xdotool keys with a hold.
- The ST `$4ba` hz_200, `_vbclock` `$462`, `_frclock` `$466` and MFP timer data registers are not read by the game code (0 hits).

## 5. Where the time is not going
Per-frame costs outside `$3990`: pace/flip/VBL spin `$5f6a` 2.5-9.5 %, `$c84a` 3.4-5.9 %, `$96f6` 3.0-5.6 %, `$269c` ~1-2 %, `$41d8` 1.5-2.4 %; everything else < 0.3 % (table above).
