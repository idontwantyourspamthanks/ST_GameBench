# Nebulus tower timing budget (8 MHz STE, Hatari 2.6.1)  (NebBoot2)

Authoritative flip count = executions of `pc=$3868e` (`move.b $38759,$ff8201` inside the flip `sub_03868a`), never register-change counts.
Scripts: `work/boot/{timing2,scenes,clock,speed,budget,roles}.py`; profiles `work/dumps/boot/{timing2,clock}/`.

## 1. Flip rate per scene [obs, `scenes.py`, 250 VBL each, snapshots]
| scene | flips | fps | VBL/flip |
|---|---|---|---|
| title / hi-score (hiscores.sav) | 90 | 18.00 | 2.78 |
| "Entering: <tower>" interlude (tower.sav +0.3 s) | 65 | 13.00 | 3.85 (6-VBL step delays, `$3db54`) |
| **tower** (tower.sav +9 s) | 125 | **25.00** | **2.00** |
Tower flip deltas in VBL [obs, `e VBL` at each flip]: standing 145/145 = 2; Right held 90 x 2 + 1 x 3. The 22.05/18.5 fps figures mix the scenes above.

## 2. The pacer ($3822c) [disasm + obs]
```
03822c  d0 = $3821a*2 ; if $38218 != 0: $38216 = word $3821c(pc,d0) else word $38220(pc,d0)     ; tower: $38218=1, $3821a=0 -> $3821c[0] = 2
038256  a0 = $38214 (tick counter)
03825c  d0=(a0) ; 03825e cmp.w (a0),d0 / beq $3825e        ; SPIN until the counter changes (>= 1 new tick, mandatory)
038264  d0=(a0) ; cmp.w $38216,d0 ; bcs $3825c             ; ... and until counter >= $38216
038270  clr.w $38214 ; rts
```
`$38214` is **not** a beam wait: it is a tick counter `addq.w #1,$38214` in `$382ba/$382c0`, the **last timer-B raster handler of the chain** (`$120` chain of `move.w $351xx,$8250` palette splits from `$341f2..$34ad4`; the VBL handler `$70=$382d8` restarts timer B each frame). One tick per VBL (entry count 160 per 80 frames). The flip waits (a) for at least one new tick, (b) until `$38216` ticks: tower table value 2 -> every tower frame takes exactly 2 VBL = the cap **25 fps**, the logic is run once per flip (frame-locked).
Cost [obs, stand profile, 80 frames = 160.1 VBL]: 320,700 cycles/frame = 2.00 VBL; spin `$3822c..$3827b` **104,245 (32.5%)**; busy **216,455 = 1.35 VBL** (VBL = 160,256 cycles at 8 MHz). Right/jump/left: busy 216-219k, same.

## 3. Per-frame cost table (stand, 8 MHz; cycles/frame; function self buckets from `nprof.py`, inclusive from `budget.py`)
| function (role) | calls/frame | cycles/frame | % of busy |
|---|---|---|---|
| `037b1c` tower surface blit: `037cd6` 27,306 + `037c06` 15,198 + `037e28` block 39,560 (masked tile blits, includes inner loops) | 1 | 93,800 incl. (the `037e28` block also holds the generic blit tails) | ~43 |
| `0374d2` (+loop `037556`, 32 iterations/frame) lower sea/water rows, early-out when `$338fe`<=0 | 1 | 41,611 | 19 |
| `036b3e` background/sky rows (`movem.l` fills from `$4b6ba` table by tower index `$3390c`) | 1 | 29,619 | 14 |
| `033f8a..` timer-B raster chain (palette splits) + VBL handler `$382d8` + tick `$382ba` | 2 (per VBL) | 18,368 + 2,336 | 10 |
| `037ffa` masked sprite blitter (and/or 4 planes) | 6 | 10,735 | 5 |
| `0370d2` | 1 | 5,912 | 3 |
| `03920c/03936a` (HUD side, per-row loop 20x) [INFERENCE: HUD/score] | 1 | 6,278 | 3 |
| sound `033d02` (YM writes `$33db2..$33e48`, once per VBL) | 2 | 2,631 | 1.2 |
| logic (`03b482/03a7fc`, `0396cc`, `03a572`, `03ae6e`, `03792c`, `0373e2`, `03b3d8`, ...) | | ~9,900 | 4.5 |
| frame pacer spin | 1 | 104,245 (idle) | - |
Roles are from the call structure and an `rts` poke test (`roles.py`, `work/dumps/boot/roles/`: rts at `37cd6/37c06` removes ledge/step tiles, `374d2` changes the water band; `36b3e` gives no visible change on a static scene because the back buffers keep the old fill) -> **[INFERENCE]** for names; the cycle numbers are measured.

## 4. Cap and headroom
- 8 MHz: busy 1.35 VBL < 2 VBL: headroom **103,800 cycles/frame (32%)** at 25 fps. Table 1 changes nothing (needs busy < 1 VBL: cut >= 56,000 cycles = 26%): `clock.py` 8 MHz table=1 -> 24.9 fps.
- Removing the spin entirely: ungated flips would draw into the buffer still displayed (base latches at the next VBL) -> tearing; the speed bound would be 1/busy = 37 fps in the average and the logic would run 1.5x fast.
- 16 MHz [obs `clock.py`/`speed.py`, Hatari `--cpuclock 16`]: shipped table: 24.9 fps, busy 216,667 cycles = 0.68 VBL (of 320,512), spin 66%; **table `$3821c`=1: all 135 flip deltas = 1 VBL = 50 fps** (`speed.py` sequence `111...`). 32 MHz: shipped 24.9 fps, busy 0.33 VBL; table=1: 45.1 fps in the profiler run (profiling overhead; the profile windows of table=1 at 16/32 MHz showed ~10% 2-VBL frames, the unprofiled 16 MHz run showed none).
- **Caveat that decides the user's question**: the game logic is frame-locked (the pacer is the only governor: 25 fps on 8, 16 and 32 MHz alike), so table=1 makes the game **run twice as fast**, not smoother. A real "50 fps" needs the logic decoupled (update every 2nd flip, draw every flip) -- not a table poke. Not built. [The timer-word measurement meant to prove 2x (`speed2.py`) was inconclusive: the player died during the run and the timer froze; the 2x follows from the code.]
