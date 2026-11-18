# Nebulus input latency (NebInput2)

All numbers: Hatari 2.6.1, STE 1 MB, TOS 1.62, tower snapshot `input/snap/play_noenemy.sav` (own snapshot, enemies off via the
NebTrainers poke `$3792c`=`4e75`, `$3398c..` cleared, so the loop is the clean 2-VBL one). Raw traces: `input/raw_*.json`;
tools: `input/tr.py` (cycle-stamped breakpoint tracer: every event logs `e VBL` + `e FrameCycles`), `run3.py`, `ana.py`, `short.py`.
Frame = 160,256 cycles at 8 MHz = 20 ms.

## 1. Input path (disassembly of the tower dump `dumps/tower_1mb.bin`)
* Host key -> Hatari -> IKBD -> ACIA IRQ `$118` = `$384fc` -> Gamex hook `jmp $200` (`$200: cmp #$c3 ...; cmpi.b #$f6,d0; bcc -> $3851a (drop); else jmp $38514`)
  -> `$38514: move.b d0,$38498.l`. **`$38498` is one "last byte" cell**, not a queue. IKBD packet headers `$fe/$ff` (>= `$f6`) are dropped by the hook,
  the joystick state byte (bit7 fire, bits0-3 up/down/left/right) and keyboard scancodes both land in the cell.
* Hatari with `--joy1 keys` sends, per host key, **two** things: the keyboard scancode immediately (RCtrl make `$1d`, break `$9d`; Right `$4d`...) and
  one frame later a joystick packet (`$ff` + `$80` fire, `$08` right, `$88` both, `$00` release). Measured order e.g. `ACIA S1d | VBL | ACIA ACIA S80`.
* The only reader is `sub_03853a` ("poll"): `$3853e move.b $38498(pc),d0; andi.b #$70,d1; bne -> key path`; joystick path
  `$3854e btst #7,d0 -> $338f0` (fire flag), `d0&$f -> $385b4/$385d4 tables -> $338f2 (dx), $338f4 (dy)`. Bytes with bits 4-6 set (scancodes, `$1d`,`$9d`) leave the fire/dir
  flags untouched (they only set menu index `$3849a`).
* The poll is called once per game-loop iteration from the loop top `$3dcf4` (`jsr $3853a`) -> **once per flip = once per 2 VBL**.
  Consumption `$3e188` (called `$3ddd0`) -> `$39c8c` (fire edge latch `$338f8`: held fire is cleared after the first loop, a fresh press needs a poll that saw 0)
  -> state-machine dispatch by `$33a20` through table `$39cd2`.
* Pacer `sub_03822c`/`sub_03868a`: loop = `[poll+logic+render] -> spin until tick counter $38214 >= $38216 (=2) -> write $ff8201/03 (flip) -> next loop`.
  `$38214` is incremented by the Timer-B raster chain's last element (`$382ba`) at **frame cycle ~134,650 = scanline ~263** of each frame, i.e. at the *bottom* of the screen,
  not at VBL. The loop therefore starts (flip+poll+CONS) at line ~263 of every 2nd frame.

## 2. Measured timeline of one loop (8 MHz, cycles from the VBL, `input/tr.py`)
```
TICK 134650 -> FLIP 134810 -> POLL 135480 -> CONS(3e188) 136230 | VBL 160256 | TICK(1st) 294800 | VBL 320512 | WAIT(=compute done, enters $3868a) 333700 (fc 13.3k)
TICK 455030 -> FLIP ...   (loop period 320,512 = 2 VBL exactly, 145/145)
```
Compute (poll -> WAIT) = 197,000 cycles = 1.23 frame; the remaining 0.77 frame is the spin (`$3825e/$38260`, the lead's 29.5% of cycles).
Hatari/real-ST latch of the video base: `Video_RestartVideoCounter` at HBL 310 (50 Hz) of the *current* frame (hatari-pist/src/video.c:4609) -> the buffer flipped at line 263
is shown from the next frame start (VBL). So **poll -> first presented frame = 3 frames minus 24k cycles = 2.15 frames (43 ms)**, constant (measured every trial).
(An earlier flip would not help at 8 MHz: the latch for frame n+2 is at line 310 of n+1, compute finishes at line ~26 of n+2.)

## 3. The jump state machine has a one-loop dead time (the dominant, fixable part)
State `$33a20`: 0 walk/stand, 1 jump, 2 land, 5 stand-fire/shoot, ... Jump entry `$39fc8` (walking + fire) and `$39ffc` (blocked), both end with `rts`
after `move.w #1,$33a20; clr $33a1e; ...; jsr $33be8`: **they only set the state**; the first step (`$3a026`: y/pose/x advance via `$39bee/$39c2e`) runs in the
**next** loop. Traced per flip (`$33a16` x, `$33a18` y, `$33a1e` step, `$33a20` state, `$33a22` pose):
```
FLIP(loop k, fire consumed)  x=17 y=8 step=0 state=1 pose=133   <- identical picture (x frozen, walking pose), state already 1
FLIP(loop k+1)               x=18 y=11 step=1 state=1 pose=128  <- first visible jump motion
```
so fire -> first visible motion = 2 loops = +2 frames after the state frame. Direction press (stand->walk) and stand-fire (state 5) have no such dead loop
(x/pose change in the first loop after the poll).

## 4. End-to-end (host xdotool key down -> first *presented* motion), 8 MHz, enemies off
(T_key = guest ACIA scancode `$1d` event, T_joy = joystick packet `$80/$88`; presented = start of the frame after the flip.) Frames of 20 ms.

| action (8 MHz, enemies off, random phase) | n | host key -> first presented motion (min/med/mean/max, ms) | poll -> presented motion (ms) |
|---|---|---|---|
| jump while moving, **baseline** | 7 (5 of 12 trials had no analysable JUMP: blocked/other branch) | 105 / 118 / 120 / 141 (T_key=guest scancode); from the joystick packet 85 / 98 / 100 / 121 | **83** (4.15 frames, every trial) |
| jump while moving, **dead-loop fix** | 7 (of 10) | 68 / 76 / 83 / 102; from the joystick packet 48 / 56 / 63 / 82 | **43** (2.15 frames, every trial) |
| jump, 16 MHz baseline | 4 (of 8) | 104 / 110 / 116 / 141 | 83 |
| jump, 16 MHz fix | 5 (of 8) | 65 / 95 / 90 / 102 (small n) | 43 |
| walk right from standing, fix active (negative control: touches no walk code) | 8 | joystick packet -> motion 48 / 60 / 60 / 73 | 43 (same as the baseline trace: poll 2,859,660 -> flip 3,179,504 -> shown 2.15 frames later) |

16 MHz changes nothing: the loop is pacer bound (poll -> presented is 2.16 frames at both clocks).

Components of the jump-while-moving delay (median, ms): host event -> guest scancode ~0-1 frame (Hatari quantises key events to its event pump); scancode -> joystick packet
+1 frame (Hatari/IKBD: `$1d` first, `$ff $80` one VBL later); packet -> poll 0..2 frames (mean 17 ms, because the game polls only at line 263 of every 2nd frame);
poll -> picture 43 ms (compute 1.23 frame + wait for the next video-base latch; structural); **+40 ms dead loop (jump only)**. So of the ~118 ms measured baseline, 40 ms (34%)
is the dead loop, 43 ms the render pipeline, ~17-37 ms sampling, the rest Hatari's IKBD path (real hardware has no scancode/packet staggering).

## 5. Short presses
* Hatari cannot make a 1-frame fire press with host keys: for 14 random holds of 7..57 ms the joystick `$80`->`$00` gap in the guest was 2.80 frames (11x) or 3.74 frames (3x)
  (`input/raw_s_base.json`, `ana_short.py`). Baseline: fire reached the state machine in 13/14 (the single miss, hold 13 ms, had a poll inside the gap and the stand-fire
  path `$3a2f8` was not entered: not explained); with the sticky latch below 14/14.
* Game side: the cell is level-sampled once per 2 VBL, so a press whose release byte arrives before the next poll is lost entirely (the cell is overwritten by `$00`/`$9d`).
  NebTrainers measured misses for taps < ~40 ms. The 1-frame pulse test (poke of `$38498` at VBL N / N+1) is in section 6.

## 6. Fixes
### Fix A (implemented as live pokes, verified): remove the jump dead loop. 2 sites, in place, no blob
```
$39ffa  4e75 (rts)  -> 60 2a   bra.s $3a026   (end of the walking-jump entry $39fc8: run the jump step 0 in the same loop)
(first version also patched $3a024 4e75 -> 4e71 for the blocked auto-hop entry $39ffc; split out as ni_hop.nep, default NO, see section 9: it changes the hop cadence)
```
Effect: poll -> first presented jump motion 83 ms -> 43 ms (-2 frames, -40 ms; measured 7+7 trials above). Trajectory check (`raw_b8_jump.json` vs `raw_f8_jump.json`, per-flip
`(dx, dy, state, step)` of 7 jumps each): baseline `0,0,1,0 | 1,3,1,1 | 2,5,1,2 | 3,7,1,3 | 4,8,1,4 | 5,9,1,5 | 6,9,1,6 | 7,9,1,7 | 8,8,1,8 | 9,7,1,9 | 10,5,1,10 | 11,3,1,11 | 12,0,2,1`;
fixed: the identical sequence without the leading `0,0,1,0` frame (all 7 trials each, every field). Same jump height/length/landing, one loop (2 frames) earlier.
Not checked: pixel-level equality of the rendered frames (the host-timed input makes a replayed compare impossible) -- the player state per frame is identical, the sprite
is selected from `$33a22`, so expect the same pictures shifted one loop `[INFERENCE]`. `jsr $33be8` (jump sound/anim trigger, `$39ff4`) still runs once, at the same instant as before.
Negative control: walk-from-standing with the patch active: poll -> motion 43 ms, the same as the unpatched trace; the patched sites are only reached from `$39fc8/$39ffc`.

### Fix B (sticky fire latch; designed + live-patched, 2 hooks + 56-byte stub): never lose a press shorter than the poll period
`$38514 move.b d0,$38498.l` (6 bytes) -> `jmp stub1`; stub1: the same move, then if `(d0 & $f0) == $80` (joystick byte with fire, no scancode bits) `move.w #1,sticky`; `jmp $3851a`.
`$3855a move.w d1,$338f0.l` (6 bytes) -> `jsr stub2`; stub2: `tst.w sticky; beq .; move.w #1,d1; clr.w sticky; .: move.w d1,$338f0.l; rts`.
Bytes: `input/short.py` `STUBS` (stub1 at `$860`, stub2 at `$880`, sticky at `$8f0`: zero area `$84c..$8ff` in all three dumps; for shipping use the blob zone `$76b10..$77ec0`).
A held press behaves as before (the latch is consumed by the first poll, the level keeps the flag); a press+release between two polls produces exactly one loop of fire, so the existing edge latch `$338f8`
still needs one poll with 0 before the next press (unchanged). Scancode bytes never set the latch.

### 1-frame pulse gate (`input/pulse.py`, `pulse.log`; 8 MHz, standing, stand-fire path `$3a2f8` as the registration probe)
Cell `$38498` = `$80` at the entry of VBL frame N (odd, i.e. the frame whose only poll is *after* the release), `$00` at the next VBL entry (pulse = exactly 1 frame; stamps e.g. VBL 3531 -> 3532):
| config | pulse spans no poll ("miss") | pulse spans a poll ("cover") |
|---|---|---|
| baseline | **0/3 registered** (all lost) | (not run) |
| stub2 live-patched + sticky set as stub1 would | **3/3 registered** | 3/3 registered (control: unchanged behaviour when the poll sees the press) |
Caveat: the pulse test pokes the sticky byte itself (stub1's effect); stub1 as code was exercised only by real Hatari packets (`s_latch`, 14/14 registered, no crash/behaviour change), not shown to set the byte `[INFERENCE]`.

## 7. Answers for the lead
(a) The only reader of `$38498` is `sub_03853a`, called once per game loop at `$3dcf4` = once per flip = every 2 VBL (25/s; 145/145 loops = 2 VBL), at line ~263 of the even frames (FrameCycles ~135,480), right after the flip.
(b) A press+release between two polls is lost (0/3 one-frame pulses registered); Hatari's own key path cannot produce a pulse shorter than 2.8 frames, so the normal user never hits this under Hatari; 13/14 random 7-57 ms host taps registered.
(c) Press -> first presented motion, jump while moving: 105-141 ms (median 118) baseline, of which 83 ms is after the poll; walk/direction 48-73 ms from the joystick packet; stand-fire/shoot (state 5) changes the pose in the first flip after the poll (single trace, 43 ms after the poll).
(d) Dominant fixable cause = the jump's dead loop (+40 ms, 2 frames, jump only). Fix A (2 in-place 2-byte sites) -> 83 ms -> 43 ms after the poll, trajectory identical. Fix B (latch) only matters for taps < one loop.
Not fixable without restructuring: the 43 ms pipeline (poll -> compute 1.23 frame -> next video-base latch at HBL 310) and the 0-2 frame sampling wait; 16 MHz gives no gain (pacer bound; the flip could move earlier only when compute < ~0.9 frame, i.e. not at 8 MHz).
With enemies on the loop is 2-3 frames (the lead's 18.5 fps measurement) and the dead loop then costs a full 2.7-frame loop: the gain of Fix A is larger there `[INFERENCE, not measured: my snapshot had enemies off]`.
Shipping: Fix A = two `nepatch` sites above (no blob); Fix B needs the blob zone + two jmp/jsr sites and stage-2 final addresses.


---------------------------------------------------------------------------------------------------------------------------------
# 8. Delivery (NebInput2, second round): shipped patch files, gates

Files: `patches/ni_jump.nep` (Fix A, 1 site `$39ffa`, default yes), `patches/ni_latch.nep` + `patches/ni_latch.s` (Fix B, 2 sites + 60-byte blob at `$76d00..$76d3b`, default yes),
`patches/ni_shoot.nep` (stand-fire dead loop, 1 site `$3a332`, default NO), `patches/ni_hop.nep` (auto-hop dead loop, 1 site `$3a024`, default NO). Generator `work/input/gen_ni.py`.
`nepatch.py verify --only ni_jump ni_latch ni_hop ni_shoot`: `271849 game bytes compared, 0 differ`, every site `dump-orig OK` (orig `4e75`/`13c000038498`/`33c1000338f0`/zeros).
Blob zone: mine `$76d00..$76d3b`; trainers `$76c00..$76c75`; the editor overlay (`ed_overlay.nep`, other agent) starts at `$76d40` (adjacent, no overlap; nepatch checks overlaps).

## 8.1 Cold-boot gates (Nebulus(game=build dir), `work/input/gate_boot.py`, raw logs `gate*_*.log`)
Build `both` = ni_jump + ni_latch (4 sites); `bad` = same with the first site's original byte flipped (`--corrupt`).
Rebuilt with the merged `tools/nepatch.py` (payload `NEPATCH.BIN` 24,580 B + `NEBLEVEL.OVL`), raw output `work/input/gate3_*.log` (script `gate_boot.py`: cold boot, `boot_to_game`-style fire start, then `m` of marker, site count, site bytes, blob):
```
GATE build/both ste:      in tower True after 23s | marker $b0020: 4e 45 50 4f (NEPO) | site count $b0024: 00 04 | $38514: 4e f9 00 07 6d 04 | $3855a: 4e b9 00 07 6d 22 | $39ffa: 60 2a | $3a024: 4e 75 | $76d00: 00 00 00 00 13 c0 00 03 84 98 02 00
GATE build/bad ste:       in tower True after 23s | marker 4e 45 50 46 (NEPF) | site count 00 00 | $38514: 13 c0 00 03 84 98 | $3855a: 33 c1 00 03 38 f0 | $39ffa: 4e 75 | $76d00: all 00   (nothing applied, unpatched game runs)
GATE build/default ste:   in tower True after 23s | NEPO | site count 00 0a (default set: trainers 3+blob, ni_jump 1, ni_latch 2+blob = 10 sites; no overlap) | same site bytes as above
GATE build/both megaste:  in tower True after 49s | NEPO | site count 00 04 | $38514: 4e f9 00 07 6d 04 | $3855a: 4e b9 00 07 6d 22 | $39ffa: 60 2a | $76d00: 00 00 00 00 13 c0 ...
GATE build/bad megaste:   in tower True after 49s | NEPF | site count 00 00 | sites original (13 c0 00 03 84 98 / 33 c1 00 03 38 f0 / 4e 75), blob zero
```
(STE 1 MB TOS 1.62; Mega STE 4 MB TOS 2.06; the corrupt build flips the first site's first original byte, `$38514` `13`->`ec`.) Fire still starts the game from the title in every build (the cold boots use fire).

## 8.2 Fix A equivalence: scripted input, enemies ON, stock vs patched (`work/input/scripted2.py`, `s3.py`, `s4.py`, `cmp_sc.py`, logs `sc/*/log.txt`)
Method: input = poke of `$38498` at the loop-top poll (`pc=$3dcf4`) keyed on the level-timer words `$3ad98/9a/9c` (they tick once per game loop, so the key is the loop index, host timing
cannot matter); chained breakpoints; per-flip log of the variable block `$33900..$3398f`+creature slots (336 bytes) + timer; screens dumped at chosen flips. Snapshot `snap/own_tower.sav` (level intro, enemies spawn normally).
Script J1 (loop numbers from the first timer tick): Right held from 45; fire pulse (4 loops) at 50 = **walking jump landing on ground**; stop; fire alone at 90 = **stand-fire/shoot**; Right again at 105 and fire pulse at 108 = **jump that lands on the crumbling tiles (x=36): landing -> state 8 death**;
fire held 120..127 = **jump pressed while the state changes landing -> death**. 
* Determinism control: stock vs stock2 (two independent restores): per-loop variable block and player vars identical in 183/183 loops; all 14 dumped frames 0 differing bytes.
* Stock vs Fix A: creatures (X,Y,frame,counter,state,speed,aux,target of slots 0-3), tower, energy, spawn pointer identical at the same loop index in every loop **except** loops 127.. where only the timer gate `$33938` and the ones-word `$3ad9c` (32 vs 33) differ: the death
  sequence starts one loop earlier in the patched run, so the timer is frozen one loop earlier (the whole player timeline is shifted). Player vars `$33a16..$33a22` differ at the same index in 87 loops, **all 87 satisfy patched[j] == stock[j+1]** (0 unexplained).
* Ran again with Fix A + shoot patch together (j1b_jumpshoot): 92/92 player-differing loops are exactly patched[j]==stock[j+1]; shot slot (slot 4: X,Y,frame,counter,state,speed,aux,target) identical to stock one loop later in 13/13 differing loops.
* **Frame buffers (pixels)** at matched states, 12 consecutive frames across the jump, enemies on (`j1b_*`) and enemies off (`j1noen_*`, creature states 0 in all 235 flips): patched frame k vs stock frame k+1,
  playfield rows 20..129 (tower, frog, ledge): **0 differing bytes in all 12 frames**; patched(k) vs stock(k) (same loop, i.e. what the unpatched game shows one loop later) differs by 3,438..3,964 bytes there (the test is sensitive).
  Residual differences only in rows 0..19 (HUD timer digits, 38..52 bytes) and rows 130..199 (sea animation, 485..626 bytes): both are driven by the loop counter (they would differ between stock frame k and stock frame k+1 too).
  The press frame itself: stock frame at the press loop is pixel-identical to the frame before (rows 20..129: 0 differing bytes, k=4 vs 5), i.e. nothing happens on screen in that loop = the dead loop, now removed.
* Blocked-walk (auto-hop) case, script J2 (solid pillar poked into the grid at x 16..23, `w $329f2 $81 $81 $81`, Right held, fire pulses at 60 and 80): Fix A only (site `$39ffa`) = **identical to stock in all 176 loops** (variable block and player vars, 0 differences): the hop entry `$39ffc` is not touched.
  With the second site (`$3a024`, now ni_hop) the hop cycle is 9 loops instead of 10 (stock hops start at loops 55, 65, 75, 85, 95; patched 55, 64, 73, 82, 91): not an equivalence, a +11% hop rate, hence split out and default off.

## 8.3 Fix B gates (real shipped code in `build/both`; stock-for-B = `build/nolatch`)
* **stub1 sets the latch from real Hatari packets**: 20 real host taps (xdotool hold 0..60 ms, `realpulse.py`, `real_rp_both.json`): every tap delivered the bytes `1d 80 9d 00`; the latch hook (`pc=$76d14`) fired 20/20, the consumer (`pc=$76d2e`) 20/20, fire reached the stand-fire handler 20/20, latch word `$76d00` = 0 after every tap.
* **1-frame pulse through the real ACIA path** (`realpulse2.py`, offline classification `pulse_ana.py`): at the real ACIA store `pc=$38514` the debugger rewrites d0 of the first byte of a tap (RCtrl make `$1d`) to `$80` and of the next real byte (the joystick packet one frame later) to `$00`:
  the game's cell sees `$80` for exactly one frame (measured press -> release gap 0.996..1.004 frame = 159.5k..161k cycles). Poll events inside the pulse are counted from the trace.
```
build/nolatch (no Fix B), 12 pulses: registered 4, lost 8.  pulses with >=1 poll inside: 4, registered 4.   pulses with 0 polls inside: 8, registered 0.
build/both    (Fix B),    12 pulses: registered 12.          pulses with >=1 poll inside: 6, registered 6.   pulses with 0 polls inside: 6, registered 6.
```
  Negative control: the unpatched build registers exactly the pulses that contain a poll (4/4) and none of the others (0/8); the patched build registers all.
* Held fire, 75 s from the tower with enemies on (`holdfire.py`, `hold_*.json`): stock-for-B and `both` end in the identical state at every 13.5 s sample (`(24,56,23), state 8`, frog drowned, game does not restart by itself): the held fire does not auto-start a second game with the latch.
* Title/menu: scancode bytes never latch (the latch condition is `(byte & $f0) == $80`, bits 4-6 clear, the same discrimination `sub_03853a` uses to route to the joystick path); fire from the title still starts the game in all cold boots above. Residual not tested: a fire tap made while the game is not polling (loader, long animations) stays latched until the next poll, so it can start the game one poll later; the stock game ignores such a tap.

## 8.4 Lag table, enemies ON, STE 8 MHz, real host keys (xdotool), n = 10 each (all 10 analysable); frames of 20 ms; `T_key` = guest scancode `$1d`, presented = start of the frame after the flip
| action | build | key -> first presented change (min/med/mean/max ms) | poll -> presented (ms) |
|---|---|---|---|
| jump while moving | stock | 107 / 129 / 126 / 142 | 83 |
| jump while moving | Fix A | 64 / 81 / 81 / 98 | 43 |
| stand fire: pose changes | stock / shoot patch | 63 / 87 / 82 / 101 (both) | 43 (both) |
| stand fire: **shot visible** | stock | 143 / 167 / 162 / 181 | 123 |
| stand fire: **shot visible** | ni_shoot | 107 / 122 / 122 / 137 | 83 |
Sampling (joystick packet -> poll) is 0..2 frames, mean 18-23 ms; the 43 ms poll -> picture pipeline and Hatari's 1-frame scancode -> packet stagger are not touched.

## 9. Other dead loops (state entries that set `$33a20` and `rts`), scan of table `$39cd2` and every `move.w #n,$33a20` site
| state | entry | what the entry does | next-loop handler | input relevant? | status |
|---|---|---|---|---|---|
| 1 jump | `$39fc8` (walk+fire) | sets state, step 0, `jsr $33be8`, rts | `$3a026` | yes | **fixed (ni_jump)** |
| 1 hop | `$39ffc` (blocked walk) | same, no fire | `$3a026` | auto | ni_hop (default no: cadence +11%) |
| 5 shoot | `$3a308` | sets state+pose, rts | `$3a334` (step 1 = `sub_03a376` spawns the shot) | yes | ni_shoot (default no): shot 123 -> 83 ms after the poll |
| 3 turn | `$39e1e` | sets state, step 0, rts | `$39e2e` (turn pose table) | yes (direction reversal) | measured in 9.1 |
| 2 land | `$39ee2`, `$3a0cc` | sets state, rts (`$3a0cc` is followed by data: a fall-through patch is not possible) | `$39efa` | no | not touched |
| 4 door, 7 hit, 9, 10 | `$3a116`, `$3a672`, `$3bb96`, `$3ba78` | set state (+ sound), rts | their handlers | no | not touched |
| 6, 8 | `$3a3d6`, `$3a74a` | state 6 branches on (`bsr/bra`), state 8 falls into its handler | - | no | no dead loop |

## 9.1 Turn (state 3) dead loop, measured (enemies on, STE, Left pressed from standing facing right, n = 8 each, `run_en.py turn`, `ana.summarize_turn`)
```
stock             poll -> first pose change 83 ms (4.15 frames, 8/8)   poll -> first x change 363 ms (18.15 frames)
live nop @ $39e2c poll -> first pose change 43 ms (2.15 frames, 8/8)   poll -> first x change 323 ms (16.15 frames)
```
The one-byte-pair fix (`$39e2c 4e75 -> 4e71`, falls into the turn handler `$39e2e`) removes the same one-loop dead time (-40 ms) from the start of a turn. Not shipped (no equivalence gate run for it); `w $39e2c $4e $71` is the live form.

## 10. Summary of what the user feels (jump while moving, stock): ~129 ms median key -> motion (enemies on, STE): 43 ms render pipeline + ~23 ms sampling + Hatari IKBD stagger ~20 ms + 40 ms dead loop (now removed).
Shoot: 167 ms median key -> shot (123 ms after the poll: pose changes at 43 ms, the shot spawns at animation step 1 = two loops after the state is set; ni_shoot makes it 83 ms after the poll).
What remains after ni_jump + ni_latch: the 2-VBL sampling (0..40 ms), the 43 ms poll -> picture pipeline (compute 1.23 frame + video-base latch at HBL 310), and on Hatari the 1-frame key -> joystick-packet stagger. 16 MHz does not change any of it.

---------------------------------------------------------------------------------------------------------------------------------
# 11. ni_shoot / ni_turn gates and recommendation (NebInput2, third round)

Harness: `input/scripted2.py` (loop-index keyed input, now also arbitrary debugger commands per event), `s5.py` (K1..K3), `s6.py` (K4, K4b, K5), `cmp_k.py` (compare), raw logs `input/sc/<tag>/log.txt`, relations printed below are the raw output of `cmp_k.py <stock> <patched>`.
Expected relation: patched loop j == stock loop j+1 for everything caused by the patched entry; creatures/timer/sea are time-driven and must be identical at the same loop index.
Scenarios (enemies ON unless `n`; every run is a restore of `snap/own_tower.sav`, input poked at the loop-top poll keyed on the level timer = loop index):
* K1: stand shot right (loops 18, 40), Left tap (58) = turn to face left, shot left (85), Right tap (105) = turn back, shot right (125), ... the frog is hit by the eye at loop ~200.
* K2n: two shootable blue blocks poked in (`$82` at col 1 rows 2,3 and col 2 rows 2,3: `w $328f2 $82 $82`, `w $329f2 $82 $82`), stand shots at 20, 45, 70; enemies off.
* K3: pillar poked into the grid (`w $329f2 $81 $81 $81`), Right held, fire+Right at x~11 (jump toward the wall) at 55 and 84 plus the blocked auto-hops.
* K4/K4b: the vertical eye (slot 0) moved to X=16 (`w $33944 $00 $10`) and Y=10 at loop 41 so that the first shot crosses it. K5: six stand-shot taps around loop 203, where the frog is hit (state 7).
* Controls: stock vs stock2 (independent restores): K1 209/211 loops, K4 158 loops: player block, creature block, timer **0 differing loops**.

## 11.1 ni_shoot (live `w $3a332 $4e $71`)
```
== k1_shoot vs k1_stock   player vars differ at same index in 20 loops, patched[j]==stock[j+1] in 20, unexplained 0 | shot slot: 52 / 52 | creature slots: 0 loops differ | $33918+energy 0 | flags 0 | timer 0
== k1n_shoot vs k1n_stock (enemies off) identical relations: player 20/20, shot 52/52
== k2n_shoot vs k2n_stock   player 15/15, shot slot 13/13, grid cells 3/3 (blue block cells removed one loop earlier: stock loops 25,50,79 -> patched 24,49,78), $33918 (cells shot) 3/3 (1,2,3 at the same shifted loops), creatures 0
== k4b_shoot vs k4b_stock   player 15/15, shot slot 30/30, creatures 0 loops differ, energy 0 (the shot is removed at X=13 when it reaches the eye: stock loop 43, patched loop 42; the eye itself is not affected in either run)
== k5_shoot vs k5_stock     player 4/5 explained: the one other loop is 203 = the loop in which the frog is hit (state 7): stock pose 128 vs patched pose 154 for that single frame, identical from loop 204 on; shot slot 13/13; creatures 0
```
* Frames (K1n 59 frames, K2n 41 frames, enemies off): rows 20..129 (tower, frog, projectile, blue blocks) patched(j) vs stock(j+1) = **0 differing bytes in every frame inside the shot windows** (K1n 48/59, K2n 39/41 frames overall; the nonzero ones are exactly the loops before each press, 17/39/84 and 19/46: see below).
  The projectile is in rows 20..129 (screen y of the shot Y=8..12), so it is covered. Rows 0..19 + 130..199 patched(j) vs stock(j) are 0 outside the shot windows; inside them they differ by 10..80 bytes (the frog's reflection in the sea).
* **Not "just shifted": one frame is dropped.** The stock entry loop shows the plain facing sprite (pose 128) for 2 frames before the animation starts (stock poses: 140 -> 128 -> 154 -> 155 -> 154 ..., patched: 140 -> 154 -> 155 -> 154 ..). Those are the frames j-1 mismatches (patched(j-1) vs stock(j)). State 5 lasts **4 loops stock, 3 patched** (k1: runs of 4,4,4,4 vs 3,3,3,3). So the shot animation is 40 ms shorter, the frog is free 40 ms earlier, and the fastest re-shot interval drops from 4 to 3 loops [INFERENCE for the max rate: durations measured, repeat-tap rate not measured].
* Not reached: a killable creature (the only reachable ones are the eye, which absorbs the shot, and the elevated walker). No score variable was located in the `$33900..$33a4f` block (not changed by any scenario); `$33918` (shot cells) and the grid are covered.

## 11.2 ni_turn (live `w $39e2c $4e $71`)
```
== k1_turn vs k1_stock      player 16/16 explained, shot 0, creatures 0, grid 0, timer 0, no unexplained block bytes
== k1n_turn vs k1n_stock    same; pixels: rows 20..129 patched(j) vs stock(j+1) = 0 bytes in all 59 frames including the whole turn (loops 58..65: 0 0 0 0 0 0 0 0)
```
State 3 lasts 7 loops stock, 6 patched. The dead frame of a turn is a duplicate of the previous picture (no pose change in the entry loop), so unlike shoot nothing visible is dropped. Gain (enemies on, n=8): poll -> first turn pose 83 -> 43 ms, poll -> first x movement after the turn 363 -> 323 ms.

## 11.3 ni_jump through the blocked route `$39ffc`
K3 (pillar poked in): both runs enter `$39ffc` 5 times (`JUMPB JUMPB JUMPB, JUMP, JUMPB JUMPB` identical sequence stock vs patched, `sc/k3_*.tok`), including one fire jump that hits the wall (`JUMP` at `$39fc8` then the wall stops x): `k3_jump vs k3_stock`: player 34/34 explained, shot/creatures/grid/energy/flags/timer 0 loops differ, no unexplained block byte.
The auto-hop entry itself is unchanged by ni_jump (J2: identical in 176/176 loops); with `ni_hop` the hop cycle is 9 instead of 10 loops (stays default no).

## 11.4 Interaction, full default set
Default set = cr_credit + ni_jump + ni_latch + nt_trainers + **ni_shoot** (11 sites). Cold boots (`gate_boot.py`, raw `gate4_*.log`):
```
GATE build/defshoot ste:     in tower True after 23s | marker 4e 45 50 4f (NEPO) | site count 00 0b | $38514 4e f9 00 07 6d 04 | $3855a 4e b9 00 07 6d 22 | $39ffa 60 2a | $3a332 4e 71 | $3dcf4 4e b9 00 07 6c 08 (trainers) | $76c00 / $76d00 blobs present | $39e2c 4e 75 (ni_turn not in the set)
GATE build/defshootbad ste:  in tower True | NEPF | site count 00 00 | every site original (13 c0.. / 33 c1.. / 4e 75 / 4e 75 / 4e b9 00 03 85 3a), both blobs zero
GATE build/defshoot megaste: in tower True after 49s | NEPO | site count 00 0b | same bytes
GATE build/defshootbad megaste: in tower True | NEPF | 00 00 | all original
```
Real host keys with the whole set (`realpulse2.py build/defshoot`): 8 real 1-frame pulses through the ACIA path (gap 0.997/1.003 frames): **8/8 registered** (3 had no poll inside = lost in stock), latch set 8, consumed 8.
All three live patches together (jump+shoot+turn) in scripted runs: `j1b_all vs j1b_stock` player 92/92, shot 13/13; `k1_all vs k1_stock` player 36/36, shot 52/52, no unexplained bytes except time-driven ones already explained in 8.2 (slot-1 draw coordinates `$3396b/$33977` while the frog moves, flyer countdown and timer ones-word after the death).

## 11.5 Recommendation
| patch | default | evidence | gameplay-speed / visible side effects |
|---|---|---|---|
| ni_jump | **yes** | state 12/12 (j1b, enemies on+off), pixels 0 in rows 20..129 for 12 frames, K3 34/34, J2 176/176, press->motion 129 -> 81 ms median | state 1 lasts 11 loops instead of 12: flight unchanged, jump starts 1 loop earlier, re-jump possible 1 loop (40 ms) earlier; the dropped frame was a duplicate |
| ni_latch | **yes** | 20/20 real taps latched+consumed, 12/12 real 1-frame pulses registered vs 4/12 stock, held fire unchanged | none while polling; a tap while the game is not polling is applied at the next poll (untested effect on loader/animations) |
| ni_shoot | **yes** (set; lead requested) | K1/K1n/K2n/K4b/K5 above: player, shot, grid cells, `$33918` shifted exactly, creatures identical, rows 20..129 0 bytes in the shot windows; press->shot 167 -> 122 ms | the 2-frame entry pose is not shown, state 5 = 3 loops instead of 4: shot animation 40 ms shorter, re-shot interval 4 -> 3 loops (up to +33% fire rate when tapping at the limit) |
| ni_turn | no (recommended yes if you accept it; user did not report turn lag) | K1/K1n 16/16, pixels 0 in all turn frames, no dropped visible frame | turn 7 -> 6 loops (-40 ms), direction reversals feel 40 ms quicker; nothing else |
| ni_hop | no | J2: stock hops at loops 55/65/75/85/95, patched 55/64/73/82/91 | blocked-walk hop cycle 10 -> 9 loops = +11% ledge-climbing speed |
Remaining lag after the set: 0..2 frames sampling, 43 ms poll -> picture, Hatari's 1-frame key -> packet stagger; the shot still appears 83 ms after the poll because it spawns at animation step 1.
