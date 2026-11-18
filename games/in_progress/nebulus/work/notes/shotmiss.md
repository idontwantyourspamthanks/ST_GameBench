# Nebulus: "the shot hits the ball and nothing happens" (NebShotMiss)

Tags: **[obs]** observed (Hatari 2.6.1 STE 1 MB TOS 1.62 or the Unicorn M68000 simulation validated against it; raw lines quoted), **[disasm]** `work/train/dis_33000_40000.txt` (linear disassembler: the
words in data and at odd entry points look odd, the real boundaries are noted), **[INFERENCE]** not proven.
Files: everything is in `work/shotmiss/` (scripts, `ledge.sav`, `attempts.json`, per-loop trajectories `traj_*.tsv`, raw outputs `results.txt`, `gates.log`, Hatari logs `sc/*/log.txt.gz`, `eq/sc/`).
Patch: `patches/np_shot.nep` + `patches/np_shot.s` (**default NO**).  Addresses = PP's RAM build (1 MB STE / Mega STE); floppy addresses in section 8.

## 0. Answer in one paragraph
It is a **stock bug, not a rule and not timing**.  The shot-vs-creature overlap test `sub_03b7d6` looks up the shot's hit-box row in a 16-byte shape table with the index `dy+7`
(`dy = shot.y - creature.y`), but for `dy < 0` (the creature is higher than the shot) the index is `$400+k`: the `andi.w #$3ff` is missing after the `addi.w #7,d0`.  The mask byte
is then read from the game's own code (`$3bbc6..$3bbcc`) instead of from the shape table, so the box has holes and for `dy = -3` it is empty.  A **hopping ball** (creature kind 1: its y rises up
to 6 units above the height the frog's shot flies at) is above the shot in 9 of its 11 hop steps, so a shot that visually runs into the ball is simply not "hit" in about **one attempt in five**
(20.3 % of all shots that reach the ball's x, 7 of 60 random shots in real Hatari, 30 of 30 deliberately chosen ones).  Walkers and anything else at the shot's own height (`dy >= 0`) are never affected
(that is why it is "typically a ball").  `np_shot` (4 bytes in place, no code, no blob) restores the intended hit box for the shot only: 0 misses in the same attempts, everything else bit-identical.
Hunches checked and **ruled out** (section 5): tunnelling, the 0/127 wrap, loop parity, frog x, 2 vs 3 VBL per loop, `ni_shoot` (neutral: 20.3 % -> 20.0 %), update order.

## 1. Reproduction recipe [obs]
Geometry of tower 1 (mission 1, tower index 0; map dump `python3 work/level/tools/nebedit.py dump originals/NEBULGX/NEBEXE.FIC 1 0`):
- ledge row 14, cols 9..13 (`$81`), reached by the lift `$85` at col 14 row 10 (end marker `$08` col 14 row 14);
- **2-block stack** = `$82` at col 12, rows 15 and 16 (the frog is at the col-13 end, x ~ 105, y = 60; each shot removes the block at the shot's row 15 = y 60..63, the row-16 block hangs above it);
- **ball marker `$30`** at col 9 row 15 = creature kind 1 (`$6c=1`, speed `$54=0` = "waits, hopping, until the frog is on its level within 32 angle units, then rolls toward it", `$37a2e`/`$3b6da..$3b73c`), x = 76, y = 60.
  (The other markers there: `$30` col 12 row 20, `$10` col 9 row 10 = walker kind 2, `$40`... eyes.)

Harness (no teleport hang: the frog is walked in 4-unit steps, `mk_ledge.py`):
1. `python3 work/shotmiss/mk_ledge.py` -> `work/shotmiss/ledge.sav` (stock game, tower 1, frog idle at x=105 y=60 on ledge row 14, spawn off `w $3792c $4e $75`, timer reset).  Temporary ground cells are poked while walking and removed again.
2. Per attempt the debugger pokes (at the loop-top poll `pc=$3dcf4`, keyed on the level timer words, i.e. on the loop index, not on host time; `hatt.py attempt_pokes`): the stack cells (col 12 rows 15,16) = 0, creature slots 1-3 state 0, slot 0 = ball (x, y=60, state 1, hop counter `$3c`, speed `$54`, `$6c=1`),
   shot slot cleared, frog x/y/state, `$33a1c=0` (facing left), then fire as REAL input: `$38498 = $80` for two loops (the game's own poll `$3853a`, stand-fire state 5, shot spawn `$3a376` at animation step 1).
3. Every flip (`pc=$3868e`) logs `$33900..$33a4f` (player, creature slots 0-3, shot slot 4, flags).  One Hatari run = 90 attempts back to back, 26 loops each (2339 loops); `hat_main.py run stock|shoot|fix|shootfix|stock_p3|fix_p3`.
4. The same attempts run in the Unicorn M68000 simulation of the game's own per-loop code (`sim.py`: poll `$3853a`, `$37898`, `$3e188`, `$3b482` creatures, `$3b9a2` shot, `$3a572` player, `$3e1c2/$3b3d8/$3ae6e/$3b0a4`; a hook on `$3b7d6` logs every overlap test and its result).
   **Validation [obs]: sim == Hatari in every compared field of every loop, 6 runs x 2339 loops, 0 differences** (`hat_runs.log`: `stock loops matched sim==Hatari 2339 differ 0 None`, same for shoot, fix, shootfix, stock_p3, fix_p3; the creature-slot/timer trace of the plain game was also matched 77/77 flips from `play_enemy.sav`, `val1.py`).
   So the thousands of sweeps below run the real game code, only faster.  Sim bases: `python3 work/shotmiss/dump_base.py work/shotmiss/ledge.sav /tmp/shot_ledge.bin` (and `work/input/snap/play_enemy.sav` -> `/tmp/shot_play_enemy.bin` for `sweep*.py`/`phase.py`/`tunnel.py`/`kinds`).

One attempt, stock, real Hatari (`traj_stock.tsv`, attempt 0: ball hops in place at x=88, frog at 104; `m` = overlap test said no, `H` = yes):
```
loop frog_x ball_x ball_y ball_st ball_cnt  shot_x shot_y shot_st shot_cnt player_st test
 0    104    88     62      1       1          0      0      0      -1       5         -        (fire loop: state 5)
 2    104    88     65      1       3        101     60      1       1       5         m        (shot spawned, first move)
 5    104    88     66      1       6         95     62      1       4       0         m        (ball at the top of its hop, dy = -4)
 7    104    88     64      1       8         91     63      1       6       0         m
 8    104    88     62      4       0         89     63      0      -1       0         H        (dy = +1: hit -> ball state 4 = dying)
```
and a stock MISS of the same kind (`python3 work/shotmiss/trace1.py 75 1 0`: ball x=75, hop counter 1, speed 0 -> it starts to roll): the shot sits at dx = 0, dy = -2 (dead centre, 2 units below the ball) and the test answers `False`.

## 2. Root cause [disasm + obs]
Main loop order (`dis` 10932-10934): `jsr $3b482` (creatures move) -> `jsr $3b9a2` (shot moves, then tests) -> `jsr $3a572` (player).  The shot slot is 4 (`$3394c`, fields `+$00` x, `+$0c` y, `+$3c` counter, `+$48` state, `+$54` direction), the frog's hit box slot 5.
**Shot handler** `$3b9a2` (dis 8634-8680): counter `$3c == $c` -> remove (range = 12 moves x 2 = 24 angle units); else frame `$3c&3`; `x += 2*$54` (`$3b9de..$3b9ec`); `y += $3b996[$3c]` (0,1,0,1,0,1,0,0,1,0..: +0..3 over the flight);
`bsr sub_03a834` (terrain test at the shot's cell; carry = shot dies, `$82` blue blocks are shot away: `$3a9ac`); **`bsr sub_03b7d6` (`$3ba10`)**: no carry = shot continues; carry = `a0` = the creature hit:
state 5, 8, 9 -> shot removed, creature untouched (stunned walker, the two eye kinds: by design); state 2 (walker) -> state 5 for `$4b` = 75 loops (stun); every other state (the ball: 1, 3) -> state 4 (dying, 7 loops), score `$3b132` (`$100`) / `$3b1c8`, sound `$33ba0`.
States 0, 4, 6, 7 are skipped by the overlap test (`$3b7e6..$3b806`): a creature that is spawning (6) or dying (4) is not hit.

**Overlap test** `sub_03b7d6` (`$3b7d6..$3b8a2`, dis 8507-8560), a1 = tested box, a0 walks slots 0-3:
```
$3b81c  d0 = (a1.x - a0.x) & $7f ; d1 = 3 (5 for the frog box)         x diff must be -3..+2 (angle units)
$3b83a  d0 += 3 ; d0 &= 7 ; d1 = d0                                      d1 = x diff + 3  (the bit to look at)
$3b844  d0 = (a1.y - a0.y) & $3ff ; if d0 >= 8 and d0 < $3f9 -> no hit    y diff must be -7..+7
$3b860  addi.w #$7,d0                                   <-- row index = dy+7 for dy = 0..7 (7..14) but $3f9..$3ff + 7 = $400..$406 for dy = -7..-1: NO `andi.w #$3ff`
$3b864  cmpa.l #$3394e,a1 / beq $3b890                    frog box: no table, always a hit inside the x/y window
$3b86e  a2 = $3b7b6 (creature table) ; $3b874 cmpa.l #$3394c,a1 / bne.w $3b884 ; $3b87e a2 = $3b7c6 (shot table)
$3b884  adda.w d0,a2 ; move.b (a2),d0 ; addq.w #1,d1 ; lsr.b d1,d0 ; bcc no_hit    bit (dx+3) of the row byte
```
The shot table `$3b7c6` (16 rows, `dy -7..+8`) and the creature table `$3b7b6`: [obs, bytes from the dump] shot rows `1c 3e 3e 3e 3e 3e 3e 3e 3e 3e 3e 1c 1c 00 00 00` (rows dy -7 and +4/+5 = 3 wide, dy -6..+3 = 5 wide, dy +6/+7 empty).
With the index `$400+k` the byte comes from `$3b7c6+$400+k = $3bbc6+k` (code: `$3bbc6..$3bbcc` = `3a 18 30 39 00 03 39`, the tail of `subq.w #4,$33a18` and the head of `move.w $33912,d0` at `$3bbc2`/`$3bbc8`).  **Measured stock hit box of the shot** (X = hit; columns dx = -3..+2; `ideal.py`):
```
dy   stock    intended        dy   stock    intended
-7   .X.XXX   ..XXX.          -1   X..XXX   .XXXXX
-6   ...XX.   .XXXXX           0   .XXXXX   .XXXXX      (dy >= 0: identical, rows 0..5)
-5   ....XX   .XXXXX           4   ..XXX.   ..XXX.
-4   X..XXX   .XXXXX           5   ..XXX.   ..XXX.
-3   ......   .XXXXX
-2   XX....   .XXXXX
```
The ball's hop table `$3b474` (y deltas by hop counter: 2,2,1,1,0,0,-1,-1,-2,-2,-4,..; one hop = 11 loops, x +1 per loop when rolling, `$3b670..$3b6c0`) puts the ball 0..6 above its landing height, the frog's shot starts at the frog's y and rises 0..3,
so `dy = shot.y - ball.y` is -6..-1 for 9 of the 11 steps.  Walkers (kind 2) keep their y: `dy = 0..3`, fine.  The creature-vs-creature test (`$3b5e8/$3b634/$3b696`, bounce when two creatures overlap) uses the same routine with the creature table and has the same hole (unchanged by `np_shot`).
[INFERENCE] The AND is simply missing in PP's/US Gold's code; the floppy build has the identical routine (section 8), so this is the original's bug, not an artefact of the HD conversion.

## 3. Miss classes (counts)  [obs, all from `results.txt`]
Attempt = one shot at one ball state.  "in range" = the shot's intended (symmetric) box overlaps the ball in at least one tested loop (so out-of-range shots and shots after the frog was hit are not counted).
Uniform grid (sim, frog x=105 shooting left, ball x 70..105, 11 hop phases, 11 fire phases, ball speed 0/+1/-1: 13,068 attempts per variant):
| class | meaning | stock | + ni_shoot | + np_shot | + ni_shoot + np_shot |
|---|---|---|---|---|---|
| HIT | the ball dies | 5092 | 5325 | 6390 | 6657 |
| **MISS_MASK** (d) in the box, test says no | the bug above | **1298 (20.3 % of in-range)** | **1332 (20.0 %)** | **0** | **0** |
| MISS_RANGE (c) | shot expires after 24 units (12 moves) before reaching the ball | 3668 | 3601 | 3668 | 3601 |
| NOSHOT | the ball reached/hit the frog before the shot spawned | 3010 | 2810 | 3010 | 2810 |
| tunnelling (a) | crossed the ball between two tests without any overlap | **0** | | | |
By ball speed (stock, in range): waiting 476/2618 = 18.2 %, rolling toward the frog 479/2299 = 20.8 %, rolling away 343/1473 = 23.3 %.
**Real Hatari, 90 attempts** (`hat_main.py`, section 1; sim==Hatari in 90/90 attempts and every loop):
```
stock    random 60 {'HIT': 53, 'MISS': 7}    targeted-miss 30 {'MISS': 30}      (the 30 are attempts the sim predicts to miss)
shoot    random 60 {'HIT': 49, 'MISS': 11}   targeted-miss 30 {'HIT': 19, 'MISS': 11}   (ni_shoot: same attempts, shot one loop earlier = other phases)
fix      random 60 {'HIT': 60}               targeted-miss 30 {'HIT': 30}       (np_shot alone)
shootfix random 60 {'HIT': 59, 'MISS': 1}    targeted-miss 30 {'HIT': 30}       (the one miss = out of range: the earlier shot expired at x=81, the ball sat at x=78 > 24 units from the frog)
```
Classification of the MISS_MASK loops (sim, 43,560 attempts, first loop with an intended overlap, misses/overlaps):
```
by dy (shot.y-ball.y) -6:190/375 -5:275/1055 -4:0/2150 -3:2296/2296 -2:2688/2688 -1:0/2066 0:0/1622 1:0/1708 2:0/1541 3:0/971 4:0/603
by loop parity       0:2686/8518 (31.5 %)   1:2763/8557 (32.3 %)
by frog x            100:939/2902 103:1033/3288 105:1122/3484 108:1162/3661 110:1193/3740   (32 %, 31 %, 32 %, 32 %, 32 %)
by hop counter       misses only while the ball is in the air (counter 0..8), never at 10 (on the ground)
```
=> the miss is a function of `dy` and `dx` only (hits at dy = -4/-1 only for some dx; dy=-3 never).  A first-overlap miss is often followed by a later loop that hits (the attempt then counts as HIT): per attempt 20.3 %, per first-overlap loop ~32 %.
(a) **Tunnelling: none.**  The shot moves 2 units/loop, the ball and the walker 1 (the eyes 1 or 2, but they absorb the shot anyway); the largest relative x step measured in 14,520 attempts is **3** and the narrowest intended row is 3 wide, so a step can never skip the box;
40 sign changes of dx between consecutive tests, 0 of them without a hit (with the intended mask).
(b) **Collision fires but the creature does not react** (by design, `kinds.py` [obs]): kind 8 and 9 (the eye discs `$40-$70`) and a stunned walker absorb the shot (`$3ba18..$3ba72`: state 5/8/9 -> shot removed, nothing else); a walker (kind 2, `$10`) is stunned for 75 loops, a second shot meanwhile is absorbed again.
Kind 1 (the ball) dies on the first real hit: `(7, 'ball', 92, 64, 'st', 4, ... [True])` then state 4 for 7 loops -> 0.  The ball only matters here because of (d).
(c) **Shot dies before reaching the ball**: range 24 units from the frog (x-1 .. x-25); `$82` blocks absorb the shot at their cell (x within col*8+2..+6, only the block in the shot's row: the 2-block stack needs the first shot for row 15, the row-16 block is hit only when the shot has risen to y >= 64 (about 8 loops = 16 units out); any `$81`-class cell in the shot's row kills it too.  Counted as MISS_RANGE above (3668 / 13,068 attempts): the frog standing 29+ units from a waiting ball cannot hit it; the ball then starts to roll toward the frog (within 32 units).
(d) **0/127 seam**: rotation-symmetric world (full ring ledge, identical rows elsewhere), the same 702 attempts shifted by 24, 40, 56, 88, 104 units: class counts identical, `attempts whose class differs from shift 0: 0` for stock and for the fix.  The compares are `& $7f` / `& 7` / `& $f` everywhere (`$3b824`, `$3a876`, ...), no seam bug.
(e) a creature in state 4 (dying, 7 loops) or 6 (spawning, 7 loops at the marker) is skipped by the overlap test; [disasm] creatures spawn once (the scan pointer `$3393c` only moves forward, `$37978..$379ca`, reset only at level start `$37816`), so a killed ball does not come back in the same life: not a source of "nothing happens" in the ordinary case.

Realistic play (`mash.py`, sim; frog at x=106, stack in place, ball waiting at its marker, fire tapped every 6 loops, 11 hop phases x 6 tap phases = 66 runs):
```
stock   {'ball killed': 46, 'frog hit first': 20}      mean 3.20 shots until the ball dies (max 4)
np_shot {'ball killed': 66}                           mean 3.15 shots (max 4)
```

## 4. Is it intended?  [INFERENCE for intent, proof for behaviour]
The shape table is a symmetric, rounded box (dy -7..+5 for the shot, a 7-wide one for creature/creature); the code path for dy >= 0 uses it exactly; dy < 0 reads code bytes.  Nothing in the game's rules (kinds 2/8/9 absorb or stun on purpose; states 0/4/6/7 are
not hittable on purpose) explains holes that depend on the sign of `dy` only, an empty row at dy = -3 next to a full row at dy = 0, and a table index $400 too large.  I treat it as a bug in the original (the user has seen it for years: consistent).

## 5. Hunches from the report, tested explicitly
| hypothesis | test | result [obs] |
|---|---|---|
| lag / hit test at the wrong moment of the 2-VBL loop | game order read from the code (`$3ddd4` creatures, `$3ddda` shot, `$3dde0` player, all once per loop, frame-locked by the pacer `$3822c`); the creature update never tests the shot (`sub_03b7d6` from a creature has a1 = creature, a0 over slots 0-3: the shot is slot 4) | the shot always sees the creatures after they moved in the same loop: no phase between them |
| shot checked before the creature moves, fast ball and shot step past each other | tunnelling count over 14,520 attempts | 0 crossings without a hit; max relative step 3 < 3-wide minimum row |
| depends on the VBL count per loop (3 VBL loops) | Hatari with the pacer table `$3821c` = 3 (`w $3821c $00 $03`): `VBL per game loop min 3.00 mean 3.00 max 3.00` (the normal runs: 2.00) | the same 90 attempts: stock 53/7 + 30/30 MISS, fix 60/0 + 30/0, i.e. **identical** to the 2-VBL runs (`hat_runs_p3.log`) |
| loop parity / frog x | `phase.py` | parity 31.5 % vs 32.3 %, frog x 100..110 all 31-32 % |
| `ni_shoot` (state 5: 4 -> 3 loops, shot one loop earlier) makes it rarer/commoner | the uniform grid with and without ni_shoot, and the same 90 attempts in Hatari | **stock 20.3 % vs ni_shoot 20.0 %** over the full phase grid: neutral.  On a FIXED list of attempts the shot lands one loop earlier, i.e. in a different hop phase, so single attempts flip (7/60 -> 11/60 here); the rate does not change.  The bug exists in the stock game (the stock runs above are the unpatched game: the snapshot's code equals the predicted stock stage-2 image at every patch site) |

## 6. The fix: `np_shot`  (default NO)
`patches/np_shot.nep`:  `site 3b87a 66084880`   (orig `66000008` = `bne.w $3b884`; new = `bne.b $3b884` + `ext.w d0`).  4 bytes, in place, **no blob, no editor-block space needed (0 of the ~236 B spare)**.
The `bne` that skips `lea $3b7c6,a2` for every box except the shot becomes the 2-byte form and the freed word is `ext.w d0` on the shot path only: the low byte of the row index ($00..$0e, or $00..$06 after the +$400) is sign-extended, which removes the $400.
`d0` is dead after the table read.  Everything else is the original: **creature-vs-creature collisions keep their stock (buggy) behaviour, the frog's hit box is untouched (it never reaches the table), the x/y windows, states, scores and sounds are the stock ones.**
Only a shot with `dy < 0` inside the x/y window of a hittable creature takes a different path.  `python3 tools/nepatch.py verify --only np_shot`: `1 verified sites ... dump-orig OK`; with the default set + np_shot: `31 verified sites, 3 clear ranges (332 B), 6 blocks` with the nepatch of the first session hour (30 sites + this one) and `27 verified sites, 3 clear ranges (332 B), 10 blocks; ZONE_STRICT=False` with NebJunkRam's current nepatch (blobs became blocks; 26 + 1).

Consequences for play: shots that visually hit a hopping ball now kill it (+ the normal kill score); balls become *easier to kill* (that is the point).  It does not make any enemy harder to avoid, and it does not change what the eyes (kinds 8/9, absorb) and walkers (stun) do.
A shot that meets an eye above/below its height is absorbed one loop earlier or later than before (stock false hit / hole), K4b: stock removes it at x=13, np_shot at x=15 (intended box).

### Gates
**Equivalence, real Hatari, scripted loop-keyed input** (`eq_run.py` + `eq_cmp.py`, scenarios of `work/input/s3/s5/s6`, per flip variable block `$33900..` (player, creatures, shot slot, grid cells, energy, flags, scan pointer) and frame buffers at the same loop):
```
j1   stock vs +np_shot: 127 loops, 0 differ; 14 frame captures, 0 bytes     (jumps, stand shot, death)
k1   210 loops 0 differ | k1n (enemies off) 207 loops 0 differ, 62 frames 0 bytes | k2n (blue blocks shot away) 151 loops 0 differ, 42 frames 0 bytes
k3   191 loops 0 differ | k5 (shots around the frog being hit) 216 loops 0 differ
k4b  160 loops, 20 differ: the shot meets the vertical eye; shot removal at x=15 instead of x=13, nothing else (eye, score, energy identical)
same with the default set's gameplay patches live (ni_jump+ni_shoot+ni_turn) vs the same + np_shot: j1 126, k1 205, k1n 205, k2n 152, k3 193, k5 216 loops all 0 differ; k4b 162 loops, 20 differ (same cause)
```
(Normal play without a shot-vs-creature overlap executes none of the changed bytes: the site is behind the x/y window test of `sub_03b7d6`, and only for a1 = shot.)
**Cold boot, default set + np_shot** (`/tmp/shotmiss_build` = `nepatch.py build --out ... --only cr_credit ed_overlay ni_ikbd ni_jump ni_latch ni_shoot ni_turn np_lift nt_trainers np_shot`; `gate_boot.py`, `edgate.py`; raw `gates.log` = nepatch of the first hour, 31 sites;
`gates2.log` = NebJunkRam's current nepatch, 27 sites):
```
GATE ste     : in tower True after 23s | marker $b0020: 4e 45 50 4f (NEPO) | site count $b0024: 00 1b (27) | $3b87a: 66 08 48 80 | $3a332: 4e 71 | $39e2c: 4e 71 | $39ffa: 60 2a | $3dcf4: 4e b9 00 07 6c 08 | $76d00: 00 00 00 00 13 c0 00 03 ..
GATE megaste : in tower True after 49s | NEPO | 00 1b | $3b87a: 66 08 48 80 | (same bytes)           [STE 1 MB TOS 1.62, Mega STE 4 MB TOS 2.06; gates.log: count 00 1f = 31]
edgate (both): PASS marker NEPO | PASS np_shot site $3b87a: '66084880' | PASS F10 (100 ms) opens the manager | PASS F10 leaves again | PASS D (100 ms) opens the manager | PASS F10 leaves the D-opened manager | PASS F10 re-enters | FAILS []
```
(screens `sh_edgate_*_manager*.png`.)  Not run: a negative-control corrupt build for this patch alone (the loader's pass 1 is generic and was gated with every other patch), real hardware, a human A/B.

## 7. A/B for the user
```
tools/play.sh --only cr_credit ed_overlay ni_ikbd ni_jump ni_latch ni_shoot ni_turn np_lift nt_trainers          # A: current default set
tools/play.sh --only cr_credit ed_overlay ni_ikbd ni_jump ni_latch ni_shoot ni_turn np_lift nt_trainers np_shot   # B: + np_shot
```
(`--original` = PP's unpatched game, where the misses are the same: the snapshots above are the unpatched game.)  In tower 1: take the lift at the right end (col 14, x ~ 115) to the ledge, shoot the stack (2 blocks), then shoot the ball hopping behind it as it rolls toward you; in A a visible hit that does nothing happens
about one time in five (more when the ball is mid-hop), in B every shot that touches the ball kills it.  Stand-fire shots only fly 24 units (3 columns): a ball further than that is out of range in both builds.

## 8. Floppy mapping [obs, `work/shotmiss/floppy_map.py`: read-only use of `tools/nefloppy.py`]
```
PP $3b87a (4 B) -> floppy $3b856     PP bytes 66000008   floppy bytes 66000008   site_equivalent True
PP $3b860 (40 B) -> floppy $3b83c    the whole test routine is the same instructions (only the table address differs: $3b7b6/$3b7c6 -> $3b792/$3b7a2)
mask tables PP $3b7c6 -> floppy $3b7a2 : equal True      PP $3b7b6 -> $3b792 : equal True
```
So the floppy game has the identical bug and the same 4-byte patch applies at `$3b856` (`66 00 00 08` -> `66 08 48 80`).  `tools/nefloppy.py` (lead-owned) needs `"np_shot"` added to `SITE_ONLY` (`{"ni_jump", "ni_shoot", "ni_hop", "ni_turn", ...}`) before `nefloppy build` accepts it (`no floppy translation` otherwise); `Plan` then maps the site with `map_addr` and checks it with `site_equivalent`.  Not built on the floppy image.

## 9. Text for `tools/nebrelease.py` DOCS (for the lead; not edited by me)
```
    "np_shot": (
        "Shot hit box: the player's shot now also hits an enemy that is above the shot's height (a hopping ball). The original lets about one shot in five fly through such a ball. Changes the original's behaviour; off by default.",
        "Shot hit box.  The game decides whether the player's shot has hit an enemy with a small shape table (a rounded box, 16 rows).  For an enemy that is HIGHER than the shot the row index was wrong by 1,024 bytes, so the\n"
        "  table lookup read the game's own code instead and the box had holes (one row empty, others a few pixels wide): a hopping ball is above the shot's height for most of its hop, and about one shot in five that\n"
        "  visibly runs into it did nothing.  The patch fixes the index for the shot only (one 4-byte edit, no new code), so the intended box is used.  Enemies at the shot's own height, enemy/enemy collisions, the eyes\n"
        "  (which absorb shots) and the stunned walkers are as in the original; balls simply die when a shot touches them.  It is a gameplay change (the original keeps its misses), so it is off by default."),
```

## 10. Not proven / limits
- A human A/B in real play: not done (default stays NO as requested).  All ball/frog placements are debugger pokes; the shot is fired through the real input path, the shot flight, hop and hit test are the game's code (sim == Hatari in every loop).
- Only kind 1 (hopping ball) was swept; walkers (kind 2) keep their y but a falling walker (state 3) or a creature on a lift/slope with `dy < 0` is affected the same way [INFERENCE: same routine].
- Real hardware, other TOS/machines for the *behaviour* test (the cold-boot gates ran on STE and Mega STE).
- The frog being hit by the ball because shots missed (20 of 66 `mash.py` runs) is a sim result; Hatari ran the attempts with fixed frog position.
