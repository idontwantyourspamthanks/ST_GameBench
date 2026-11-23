# Enemy limit: 4 active creatures, a forward-only spawn queue (NebEnemyLimit)

Question: user packed an area of a custom tower with enemies and saw only 4. Disassembly `work/train/dis_33000_40000.txt` (game addresses), Hatari 2.6.1 run `work/enemy/e8.py`, counts `work/enemy/count.py`.

## 1. Spawner `sub_03792c` (called once per game-loop iteration from `$3df42`)
- **4 creature slots**, struct-of-arrays at `$33944` (word field F of slot s = `$33944 + F + 2*s`, field stride `$0c` = 6 words; slot 4 `$3394c` = player shot, slot 5 `$3394e` = player hit box; state word at `+$48`, slots 0-3 = `$3398c..$33992`).
  `037962: move.w #$3,d7` / `037966: cmpi.w #$0,$48(a0)` / `03796c: beq $37978` / `037970: addq.w #2,a0` / `037972: dbra d7,$37966` / `037976: rts`: no free slot (state 0) among 4 => return, **scan pointer does not move**.
- Rule = **first come in scan order, global queue**. Scan pointer `$3393c` (long, into the grid at `$327f0 + col*$100 + row`), reset only at level decode `$37816: move.l #$327f0,$3393c` (and never moved back by anything else: only writes `$379ca`, `$379f6`). Per call: `037990: cmp.b $3391b.l,d0 / 037996: bcc $37abe` = stop while row >= `$3391b` (low byte of `$3391a = ($b0 - $338fe) >> 3` (`03794a..037956`) = the row at the top edge of the screen). Otherwise walk col 0..15 of the current row (`$3799a`: `move.b (a1),d0 / bmi / andi.b #$70 / bne $379d2`), one row per call when empty (`$379a8..$379ca`: col+1 wraps, then row+1); first cell with bit7=0 and `v&$70 != 0` becomes the enemy (`$379d2..$37abc`: x=`(col*8+4)&$7f`, y=row*4, state `$48 = 6`).
  So order = **row-major from row 0 (bottom), column 0..15 inside a row**; rows are released as they reach the top of the screen; only ONE enemy per frame; a marker is never skipped or lost, it waits: the pointer stalls on the first marker that finds all 4 slots busy, **and every marker behind it (also far above) waits too**.
- Slot freeing: shot enemy -> `$3b590 move.w #0,$48(a1)` (death anim state 4, `$3c==6`); scrolled off the bottom -> draw routine `sub_0394fe`: `03955a..039566: d0 = $a0 - $338fe - 2*y`, `039592: cmp.w #$b0,d0 / 039596: bge $395aa / 0395aa: move.w #0,$48(a3)` (= enemy 16 px below the screen bottom: slot freed); `039566: cmp #$fff0 / 03956a: ble $395a8` = above the top: just not drawn, **slot stays occupied** [disasm]. Also `$3b3c0` clears all on level start/death. Time-waster flyer (state 7) also takes a free slot at the end of the tower (`$37abe`).

## 2. Global or per section?
Global for the tower: 4 at a time, never per window/row band. But the *queue* is windowed by time: markers enter only after the top of the screen has passed their row, and creatures leave the table only when killed or 16 px below the screen bottom. A packed area therefore shows the first 4 in (row, column) order; the others appear as these are shot or the frog climbs on (they scroll off the bottom). Because the pointer never goes back, enemies that scrolled off below (or were shot) never return when the frog falls down; the pointer resets only on level (re)decode (death/restart).
Consequence for the report: a packed block with long-lived enemies (eyes, balls that wait) gives 4 visible ones until the frog moves/kills; the rest are not "missing", they are queued.

## 3. Original towers (`work/enemy/count.py`; markers = bit7 clear and `v&$70`, includes markers inside lift shafts)
```
M1 T1 rows 47 enemies  9 max-in-22-row-window 6 | M2 T1 rows 54 enemies 12 max 6
M1 T2 rows 71 enemies  8 max 4                  | M2 T2 rows 56 enemies 10 max 7
M1 T3 rows 49 enemies  6 max 4                  | M2 T3 rows 54 enemies  8 max 5
M1 T4 rows 66 enemies 12 max 7                  | M2 T4 rows 64 enemies  5 max 4
M1 T5 rows 96 enemies 19 max 7                  | M2 T5 rows 56 enemies  7 max 7
M1 T6 rows 64 enemies 14 max 7                  | M2 T6 rows 94 enemies 14 max 8
M1 T7 rows 80 enemies 21 max 9                  | M2 T7 rows 80 enemies 20 max 9
M1 T8 rows 96 enemies 18 max 8                  | M2 T8 rows 96 enemies 18 max 8
```
Yes: every tower except M1 T2/T3 and M2 T4 has more than 4 markers inside one screen-high (22-row) window; the original design relies on the queue (total up to 21). [INFERENCE] shipped towers keep them spread so the frog kills/leaves them in time.

## 4. Hatari confirmation (`HOME=/tmp/nebenemy/home python3 work/enemy/e8.py`)
Cold boot, cheat, F1 restart, then via debugger: `w $327f0+$600+5` = 8 x marker (the debugger takes decimal: `60` = `$3c`, a waiting red ball `$30` marker) in column 6 rows 5..12, scan pointer `$3393c` rewound to `$327f0`. Raw (x,y,state,kind) per slot:
```
t 1 scan ptr 000327f0 [(52,22,1,1),(68,20,6,8),(52,24,6,1),(52,28,6,1)]
t 3 scan ptr 00032ef7 [(52,26,1,1),(68,19,8,8),(52,24,1,1),(52,28,1,1)]
t 7 scan ptr 00032ef7 [(52,26,1,1),(68,23,8,8),(52,24,1,1),(52,28,1,1)]
grid col 6 rows 5..12 3c3c3c3c3c3c3c3c
```
x=52 = column 6: only 3 of the 8 markers spawned; slot 1 is the level's own eye (kind 8). The pointer stalls at `$32ef7` (col 7/row 7 offset `$707`, i.e. right after the 3rd marker at row 7) for the 5 s sample; markers rows 8..12 remain unspawned (the 4 slots stay full while the frog is alive and shoots nothing). Screenshot at the end was after the frog's death/restart (not usable); the evidence is the slot RAM.
Earlier runs (markers at rows 14..21 above the scan limit ~13) spawned nothing until the pointer reached them: confirms the `$3391b` gate.

## 5. Options (nothing implemented)
**(a) Editor warning** (cheap, safe): in `place_enemy` (`patches/ed_editor.s:1167`, called by `pe` for every enemy marker), after `place`, count enemy cells (`bit7=0, v&$70`) in the grid column-major window of the 22 rows ending at the cursor row (all 16 columns x 22 rows = 352 cells, loop ~12 insns) and if > 4 set `vMsg` to a new string ("5+ enemies on a screen: only 4 show at once"). Cost estimate [INFERENCE]: ~60-70 B code + ~45 B string = ~110 B; editor has 278 B free overall (36 B in CODE1 where `place_enemy` lives, CODE2 90 B, DATA 108 B: the string fits DATA, the routine may need CODE2 + `bsr`, or reuse `colbase`). Risk: low (editor-only, `vMsg` mechanism exists, the other two warnings already use it); refusing placement is not advisable because the original towers exceed 4 per window and the game queues them. Warn-only is the honest fix; must run `gen_ed.py`'s budget and the editor gates.
**(b) More slots** (expensive, risky; not recommended for a patch release): the table is packed: `$33944 + 6 words` per field with `$339bc` (flyer countdown), `$339be` right behind the last field (`+$6c..$77`), the sort list `$339d2..$339e9` (`$3b3d8`: 5 entries + terminator, `lea $339d2`, `$339ea` current ptr) and the lift return queue `$339ee`. Going from 4 to N creature slots means relocating all 12 fields (>=6+? words), moving the shot/hit-box slots (`$3394c`/`$3394e` hard-coded at `$3a2fa`, `$3a376`, `$3a4e6`, compares `$3b80e/$3b864/$3b874`) and patching every loop count: spawn `$37962 d7=3`, update `$3b488 d7=3`, sort `$3b3ea d7=4`, clear `$3b3c6 d7=4`, hit test `$3a510`/`$3b7da`, draw `$39608`, plus a larger sort list. Needs ~2*12*(N-4)... roughly 24 B RAM per extra slot (12 fields x 2 B) in a block that does not exist near `$33944`; the nearest free zones are the verified-zero gap at `$76c00` (118 B used by trainers) or elsewhere (see `conveyors.md` 'free at run time'). Per-frame cost: update + sort + draw per active creature (the sprite blit `sub_0394fe` dominates; no figure measured) so 8 slots roughly doubles worst-case creature time; the frame budget of 131,448 cycles is already tight in busy towers (`liftperf.md`). Also behaviour changes (every original tower becomes harder: up to 9 live enemies per window) and the NEBSAVE/gates compare creature slots. Not worth it for the editor use case.
