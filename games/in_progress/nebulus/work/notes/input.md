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
$3a024  4e75 (rts)  -> 4e71    nop            (end of the blocked-jump entry $39ffc: falls into $3a026)
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
