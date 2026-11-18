# Moonshine Racers: tighten-C, the logic stage (item 4)

Agent MSRTightC. Machine for every cycle number: Hatari 2.6.1, STE TOS 1.62, 1 MB, 8.02 MHz, 50 Hz, tick patches OFF (`work/hud/build/cyc3.py` recipe, copy `work/tightC/cyc3.py`), current default HD set without mt/mx (`mr_edge rd_geom rd_draw rd_init hd_stage hd_init hd_clouds hd_nomap hd_nomap2`, "new").
Raw outputs: `work/tightC/res/`. Evidence tags: disassembly lines come from `tools/m68dis.py` on RAM dumps taken in the runs (`work/tightC/res/ram_*.bin`), cycles from Hatari `profile save` (per instruction) or from `cyc3.py`. `[INFERENCE]` marks what no tool output here proves.
Patches (all `default: no`, self-contained, blob range `$B6800-$B6FFF` only, one 2-byte `; data:` flag at `$B6FF0`, no `; ram:`): `patches/tc_clr.s` (exact), `tc_clrx.s` (fast alternative, conflicts with tc_clr, needs a named gate mask, section 5), `tc_ord.s tc_dist.s tc_hit1.s tc_hit2.s tc_proj.s`. Tools: `work/tightC/msrpatch_priv.py` (private copy; `MSR_PATCHDIR=work/tightC/pd` = the other patches without the other agents' work-in-progress files, `tc_*` symlinked), `prof_run.py` (live set + Hatari profile), `bucket.py`/`incl.py`/`dp.py` (per function / per stage / annotated disassembly), `emgate.py`, `emmut.py`, `cover.py` (Unicorn exact-68000 gates), `exp_state_tc.py` + `cmpstate_tc.py` + `run_gate.sh` (Hatari state gate), `cold_tc.py` (cold boot + drive).

## 1. The logic stage is cheap: cost breakdown (race_start driving, per pass, 70 passes of `prof_run.py race_start new`)

The profile has the idle wait `$d206` in it (tick off), 618,841 cycles/frame; the pass without wait is 491 k (cyc3). Cycles are inclusive of callees (static call graph over the profile buckets, `incl.py`), exclusive of interrupts.

| stage (call in the pass loop `$7a88-$7b64`) | what it does (disassembly + state touched) | driving | standing (grid) |
|---|---|---|---|
| `f9fa fb96 fc2a fc80 fce4 fd64 11396 1125c 113d4 1147a 11792 11230` (12 calls) | race state machine flags, voice/radio timers, start-light bookkeeping (`$1024/$1027/$1214-$1217`, `$11d9`, `$2c68` slot 12 flags): each < 250 cycles | 1.5 k total | 1.4 k |
| `10ca6` | joystick/steering/speed: `$6105` bits, speed accumulator `$10d8`, `divu.w #9` (136 cycles) -> `$130c` | 2.8 k | 2.4 k |
| `fe50` / `ff76` / `1003c` | the three ring generators, one sample per world unit of `$130c` (rings `$13b0/$17b0`, curve `$1bbc`, hill `$23c8`); ~100 cycles per unit per ring | 2.4 k / 0.7 k / 1.3 k | 0.04 k each |
| `fa2c` | scan of the 32 rolling slots for frame `$21` (finish line) | 1.3 k | 0.1 k |
| `17c24` | zero `$4b88-$4ff7` (`017c2a move.w #$46,d7`, `017c36 movem.l d0-d3,-(a0)` x 71 from `$4ff8` = 1,136 B; `road.md` says `$4b78`, that is wrong by 16 bytes: the pointer long `$4b84` survives the clear), the road stream terminator | 3.7 k | 3.7 k |
| `10a5e 10a98` | horizon scroll bookkeeping `$12f8..` | 0.4 k | 0.4 k |
| `e218` | spawn of the next scenery object from the list `$133a` (rare) | 0.3 k | 0.07 k |
| `e2e8` | `$20(slot) -= $130c` for the 32 rolling slots `$2d80+n*$38`, clears the active bit when it goes negative | 2.5 k | 2.3 k |
| `1182e / 11a3c` | AI cars `$2ca0` (4) overtaking and position `$10ca` | 1.8 k + 0.5 k | 1.6 k + 0.5 k |
| `e316` (loop `e338`) | projection of the 36 slots (32 rolling + 4 AI): 23 active slots/pass, each ~640 cycles (3 multiplies 3.3 k) -> slot x/y/scale `(a0) $2 $a $12 $2c $32`; every active slot ends visible (`$7fff` marker path never taken in the traced scenes) | 14.8 k | 12.0 k |
| `18888 / 18c86 / 18f0e` | collision scan of the player against the 32 rolling slots (dist `$12-$29`), hit effects, 3 special slots | 3.6 k + 2.2 k + 0.2 k | 3.5 k + 2.0 k + 0.2 k |
| `e406` head (sort + order list) | 5-element exchange network for the car slots, merge with the scenery ring into `$36e8` (37 entries) | 7.5 k incl. dispatch loop | 7.4 k |
| `e598` front ends + `ecc8` (type 0, 16 calls x ~430) / `e5c6 e620 e718` (types 1-3, 9 calls x ~650) | per-slot activity test, bitmap table lookup, clip, kernel-table choice, then `jsr (a4)` into the kernel | 10.7 k + 7.1 k | 7.8 k + 6.3 k |
| (not mine) `112c4 / 11342` | player-car dust sprites via `ed74` (sprite work) | 6.1 k + 7.0 k | 0.1 k |

Pure logic (`f9fa..11396` + rings + `fa2c`) is about 14 k; with `17c24`, `e2e8`, `e316`, `1182e/11a3c`, collisions and the object-stage head/dispatch (everything before the sprite kernels) about 60 k = 12 % of the 491 k pass. The 36 AI slots and the objects are NOT cullable: all 23 active slots of a pass are projected and all end visible, and every output field is state in the gated range, so a skipped slot would change `$2c68-$34ff`. The only exact savings are cheaper ways to compute the same values.

## 2. Patches and measured savings

Savings = mean of (stock-of-this-study minus patched) cycles per pass over the same pass counter `$100e` (cmpcyc.py, `cyc3.py` windows of 150 passes, 156-166 common passes), "new" = current default HD set, interrupts included, 8 MHz, tick off.

| patch | site | what (exact semantics, see the patch header) | driving | standing |
|---|---|---|---|---|
| `tc_clr` (exact) | `$17c24` | zeroes only what the previous geometry run wrote there: the old stream `p-$4f87` (p = the pointer long `$4b84`, validated: `$4b88 <= p <= $4f78`, multiple of 8) with descending `movem.l d0-d7`; first call after game start or an invalid pointer: the stock loop. Memory after the call identical to stock (section 5) | **1,939** | 1,841 |
| `tc_clrx` (fast, NOT exact) | `$17c24` | clears 16 bytes `$4f78-$4f87` (the terminator the draw's end test reads); leaves stale records below the stream start; needs the named gate mask TC_GEOM (section 5) | 4,317 | 5,665 |
| `tc_proj` | `$e316` | whole routine as a blob: `moveq #9/asr.l d3` -> `asl.l #7/swap` (low word identical); `$1e(a0) == 0` (always in the first level, 4522/4522 active visits) skips `mulu/lsr/sub/neg/add`; type-2 slots run the stock code | **1,879** | 1,332 |
| `tc_dist` | `$e2e8` | 4x unrolled, `sub.w d0,$20(a0)` in memory, restore + bclr when negative (stock leaves `$20` unchanged) | 1,079 | 796 |
| `tc_hit1` | `$18bf4` | one-test filter (`dist-$12` unsigned `<= $17`) in front of the stock collision loop; first candidate hands over to the stock loop head `$18bfa` with `a1/d7` as the stock loop would have them | 515 | 1,252 |
| `tc_hit2` | `$18c86` | one-test filter on the flags word (`not.w / and.w #$0110`), hands over to `$18c8c` | 935 | 724 |
| `tc_ord` | `$e406` | the object stage entry: stock sort and merge (same `$36e8` list), dispatch loop without the stack frame d7, inactive slots skipped without `bsr`, type 0 / frame != `$21` runs the stock `$ecc8` code inlined (flags read once into d1, no `bsr/rts`, no d6 push, same kernel call `jsr (a4)` with the same registers), everything else through the stock `$e598`; the special entry `$2a0` runs stock `$e4fe-$e566` in place under a stock-shaped frame | 1,220 | 1,258 |
| **all six with exact `tc_clr`** | | | **7,252** = 0.045 VBL | **9,244** = 0.058 VBL |
| all six with `tc_clrx` instead | | | 9,667 (speech 9,803 / no speech 9,495) = 0.060 VBL | 11,067 (11,057 / 11,121) = 0.069 VBL |

The extra frames (`mx_sync`) call `$17c24 $e2e8 $e316 $e406` too, so each extra frame gains about 1.9 + 1.1 + 1.9 + 1.2 = 6.1 k as well (8.5 k with `tc_clrx`) (`[INFERENCE]` from the per-stage numbers; the extras gate below proves state, not their cycle count).
Patches I looked at and did NOT build: sort-merge sentinel (counted: +216 cycles, loses on the exhausted-car iterations), `fa2c` unroll (0.3 k), ring generator rewrites (the `moveq #0,d6 / and.w $13a8.w` mask is self-modified per level: ~0.6 k for a risky copy), hoisting `$1316/$13ae` into registers in `e338` (no free register; net 0), composite front ends `e5c6/e620/e718` (~1.2 k for a long copy, overlap with kernel-side work), road draw/geometry/HUD/sprite kernels (other agents).
Floor: after these, `e338` is 13 k (23 slots x ~565: 3 multiplies 3.3 k, the rest instruction-bound), the object glue about 9 k + 7 k + 6 k, rings 5.7 k. Realistic further exact gain in the logic stage `[INFERENCE]`: below 2 k.

## 3. Gates (raw)

1. `msrpatch.py verify` (real tool) and `work/tightC/msrpatch_priv.py verify`: `verify: ALL OK` (`res/verify_priv.txt`); the real tool `build` (HD and `--floppy`, all defaults + the six) builds ("tc_ord / tc_proj" site lines, no error); my private builds without other agents' WIP files in `work/tightC/pd`.
2. **Exact emulator gate** (Unicorn 68000 model `work/extrap/emu.py`, whole 1 MB RAM including both screens compared after EVERY pass, masks: the payload area `$B2700-$E83FF`, stack `$77D00-$77FFF`, `$611A-B`, I/O, the road geometry output `$4724-$4F77` = the HUD gate's mask; `emgate.py`): stock vs stock+tc and "new" vs "new"+tc, dumps `h_{start,up,grid}_7a88.bin`:
```
res/emgate_1000.txt (REF=new, patched = new + all six), 1000 passes each, schedules zig, upleft, brake, up on start and up:
  h_start zig 1000: passes_with_diff=0 differing_addrs=0     h_up zig 1000: 0 / 0
  h_start upleft 1000: 0 / 0   h_up upleft 1000: 0 / 0   h_start brake 1000: 0 / 0   h_up brake 1000: 0 / 0   h_start up 1000: 0 / 0   h_up up 1000: 0 / 0
each patch alone, 200-400 passes x start/up/grid: tc_clrx, tc_ord, tc_dist, tc_hit1, tc_hit2, tc_proj: passes_with_diff=0
```
   Negative controls: `tc_clrx` without the terminator and `$4f7a-$4f7d` poked to `ffffffff`: 20/20 passes differ (9,346 addresses; with the real blob and the same poke 0); `tc_ord` with `jsr $ecc8` removed: 20/20 passes differ; skipping the special entry: crash; `tc_proj` with `lsr.l #5` / `asl.l d3,d5` mutated: rare paths differ (356 / 142 / 232 addresses).
   Rare paths forced by pokes (`emmut.py`, same pokes in both, 6 passes, instruction-hook coverage counted): type 2 and `$1e != 0` slots in `tc_proj`; flags bit 2 / no bit 7 / both / frame class `$f` (`lea $3a14`) / invalid class in the inlined type 0 of `tc_ord`: 0 differing addresses in every mode, each path executed (counts in the run).
   Hit paths of `tc_hit1/2` (4 hit labels each): 17-112 executions per label over 400-pass runs on start/up with zig/upleft/brake (0 on the standing grid): 0 differing addresses.
3. **Hatari state gate** (`exp_state_tc.py`: the HUD gate recipe, 7,306 bytes per pass at `$7b86` keyed by `$100e`, mask = the HUD-private variables + display scratch of `cmpstate_tc.py`; A = stock, TC = default tick set + the six with the EXACT `tc_clr`, XC = default extras set + the six). The inherited display-scratch mask entry "road geometry output `$4724-$4f77`" is now a NAMED entry TC_GEOM in `cmpstate_tc.py` and switched OFF with `--nogeomask`; raw `res/gate_cmp_nogeom.txt` (re-run after the exact `tc_clr`, logs `res/gate_log2.txt`):
```
start_A8 vs start_TC8   --nogeomask: common 196 (keys 96..291), 1429624 bytes compared, differing addresses 0
drive_A8 vs drive_TC8   --nogeomask: common 268 (keys 0..1706: time-out and restart inside), 1954792 bytes compared, differing addresses 0
start_A8 vs start_XC16 / XC32 --nogeomask: differing addresses 1342 / 1361, ALL inside $4724-$4f77 (checked: 0 outside), and drive_A8 vs drive_XC16: 174, same region
```
   The XC rows differ in the geometry region only because the extra frames re-run the road geometry at extrapolated poses (the region at `$7b86` holds the last extra's output; the number of extras differs between runs with different pass speed): that is the original reason for the TC_GEOM mask, it is NOT a tc effect (TC8 without extras: 0 with the mask removed). With TC_GEOM on, as in the earlier XC gate: 0 differing addresses for XC16/XC32 start and XC16 drive (the first run of this gate set, `res/gate_cmp.txt`, used the old `tc_clr` = today's `tc_clrx`).
   negative control (tc_dist with `subq.w #2`): 101 common passes, differing addresses 362 (20,631 bytes).
4. Cycles (above): `res/cyc_*.json`, `res/cyc_items2.txt`.
5. Cold boots of `build/tc_default` (private tool, default set + six): STE TOS 1.62 1 MB: boot_to_race True (vbl 5809), marker `MSPO`, the six sites patched; drive 122 s: 1,250 passes (`$100e` 59 -> 1309) in 6,097 VBL = 4.9 VBL/pass (T=30 held at 8 MHz), `$5ff8` 9,363, no crash (`res/cold_ste1024.txt`). STE 4 MB: True (5810), 480 passes in 40 s (`res/cold_ste4096.txt`). ST TOS 1.04 1 MB: boot_to_race True, 421 passes in 40 s (`$100e` 59 -> 480). Mega STE TOS 2.06 4 MB: True, `$100e` 86 -> 506 in 40 s (6 VBL per pass at its 60 Hz = 10 passes/s) (`res/cold_st_megaste.txt`; 40 s drives, not 2 min).

## 4. Unproven / risks
- Hatari + Unicorn only, no real hardware. 60 Hz and the floppy build were not run (the patches are pure 68000 code in the game image and blob area; the real tool builds the floppy set).
- Masks: with the exact `tc_clr` the TC gate needs no mask on the road geometry region (section 5). `tc_clrx` would need TC_GEOM. `$36E8-$36FF` (order list scratch) stays masked as in the HUD gate; `tc_ord` writes the same list as stock (emulator gate: whole RAM compared, no mask there).
- `tc_ord` calls the kernels exactly like `$ecc8` but not through `$ecc8`: a hook at `$ed6e` (`jsr (a4)` in stock) would be bypassed for the rolling-scenery type-0 draws (the player/AI slots through `$e568` still use it); hooks in the kernel tables / kernel entries are seen. Registers d2/d5 at the kernel call are the stock leftovers, d1/d3/d4/d6/d7 as in stock; d6 is no longer pushed (the kernel may clobber it, nothing reads it afterwards on this path).
- `tc_hit1/2` hand over to the stock loop after the first candidate: if that stock loop is hooked elsewhere the hook still sees it.
- `tc_proj`: d3 and the high word of d6 end differently from stock (nothing reads them: the next stage `$18318` loads d5, d7, a0, d2, d1, d6, a1 itself, `018318-01833a`; a1/a3-a6 are left as in stock; proven by the state/pixel gates).
- Hatari's `cyc3` windows include random speech phases; savings are per pass counter, speech and no-speech passes are given separately.

## 5. `tc_clr`: what differed from stock, who reads the region, and the exact variant

**(0) Correction.** Stock `$17c24` clears `$4b88-$4ff7`, not `$4b78-$4ff7` as `road.md` says: `017c2a: move.w #$46,d7` (71 iterations) with `017c36: movem.l d0-d3,-(a0)` (16 bytes) from `$4ff8` ends at `$4ff8-$470 = $4b88`. The start-pointer long `$4b84` and table `$4aa4` (`$4aa4-$4b83`) are outside it (Unicorn, `res` run `emstage.py`: after the stock `17c24` the pointer `$4b84` still holds the previous stream start, e.g. `ptr a 0x4cf0`).

**(1) What the first version (now `tc_clrx`, clears 16 bytes `$4f78-$4f87`) leaves different from stock.** Memory region `$4b88-$4f77`, bytes below the CURRENT stream start `p = [$4b84]` (stock: 0) that an earlier, longer stream wrote and a shorter stream did not overwrite. Measured with the geometry mask removed (`UNMASK_GEOM=1`, `emgate.py`, "new" set vs "new + tc_clrx", whole RAM compared after each pass, `res/stale_stats.txt`):
```
start zig   1000 passes: 841 passes differ, up to 367 bytes, addresses $4c00-$4def (395 distinct)    start brake 846 passes, max 173, $4c00-$4d47
up    zig   1000 passes: 898 passes differ, up to 365 bytes, $4c00-$4def                              up    brake 883 passes, max 365
grid (standing)  zig/brake 1000 passes: 0 (the stream length never shrinks)
```
At the stage boundaries (`emstage.py`): right after `17c24` the region differs from stock in 500/500 passes (the old stream is still there), after the geometry in 394/500. Nothing else differs (no byte outside `$4b88-$4f77`).

**(2) Why the stale bytes are unreadable** (every reader of `$4b88-$4f87`):
- Static (`res/static_refs.txt`, linear disassembly of `$7000-$18fff` and the blob area for any operand `$4b78-$4ff7`): the geometry stores (`$0101c8 lea $4f78.w,a6`, `$0102b4 move.l a6,$4b84.w`; rd_geom `$b42aa`/`$b42ee`), rd_draw `$b5024` and `$b5442` `movea.l $4b84.w,a1`, rd_geom's copy-back bound `$b4040`/`$b4316 cmpa.w #$4f78`; no other instruction mentions the range (the `$b70d8` hit is the patch tool's site table holding rd_draw's original bytes, not code). mx_sync's undo tables `UTAB/RTAB` (`mx_sync.s` lines 391-405) contain no address in `$4b88-$4ff7`; neither do mx_pre, mt_*, hd_stage.
- Dynamic (`rtrace.py`, Unicorn read hook with the PC, `res/read_trace.txt`, stock and "new" set, 200-300 passes, scenes start/up/grid): the only readers are the road draw reading upwards from `p`: stock `$017c62 $017c64 $017c68 $01804e $018050` (`move.w (a1)+ / move.l (a1)+` incl. the end test), rd_draw `$b503c` (`movem.w (a1)+,d0-d3`) and `$b540a` (`move.l 2(a1),d0`, the end test): every read has address >= p ("below stream start: 0" for every PC; max address `$4f7d` = the terminator long at `$4f7a`), and rd_geom's capture loop `$b430a` (`movem.l (a0)+,...` over `$4724-$4f77` into SAVE: 252-1,260 reads of which 94-394 below the stream start in the up/grid runs). `$b430a` only copies the bytes (stale or zero) to `SAVE`; rd_geom's standing-frame copy-back (`$b4040` loop) writes them back to the same addresses; neither interprets them.
- rd_geom's 33-word key `sigtab` (`rd_geom.s` line 286: `$1308 $130a $130c $1316 $1318 $13ae $1bba $1bb8 $23c6 $102c $13a2-$13ac $23bc $23be $27c8 $1bb0-$1bb6 $23c0 $23c2 $27da-$27d4`) holds no address in the region; the comparison reads those words, not the buffer.
- HUD / message code: hd_stage and the stock ticker/face run in the traced passes; none of their PCs appears among the readers.
So every semantic reader starts at `p` and stops at the terminator `$4f7a` (zeroed by both variants); the stale bytes are only ever copied.

**(3) The exact variant is now `tc_clr`** (the fast one is kept as `tc_clrx`, `conflicts: tc_clr`). It zeroes exactly the previous stream: invariant "`$4b88-$4ff7` is zero except the old stream `[p,$4f78)`" (true after every stock clear and every geometry run, because the geometry writes only the stream there), so zeroing `[p,$4f88)` restores the stock state (the stock clear leaves `$4b84` and `$4aa4-$4b83` alone too). Guards: flag byte `$B6FF0` (zero in the image: the first call after game start runs the stock loop), pointer outside `$4b88-$4f78` or not a multiple of 8: stock loop. Cost: `L = $4f88 - p` (about 700 bytes) at 2.3 cycles/byte -> saves 1,939 (driving) / 1,841 (standing) instead of 4,317 / 5,665.
Evidence: emulator gate "new" vs "new + tc_clr" with the geometry region NOT masked: 9 runs of 1000 passes (3 scenes x zig/brake/upleft): 0 differing addresses (`res/emgate_clr_exact_unmasked.txt`); region `$4b78-$4ff7` equal after `17c24` AND after the geometry in 500/500 passes x 3 runs (`emstage.py`); Hatari TC vs stock with TC_GEOM removed: 0 (section 3).
Interaction with rd_geom's standing-frame copy-back: it saves and restores `$4724-$4f77` whole, which is stock-identical state with the exact variant (SAVE then holds zeros below the stream, as stock).
Registers: `tc_clr` clobbers d0-d7 and a0 (stock d0-d3, d7, a0) and preserves a1; the callers are `$7afe` (followed by `jsr $100b4`) and mx_sync `jsr $17c24 / jsr $100b4`, and `rd_geom` starts with `move.w $130c.w,d0` / its own `lea`s, so d4-d6 are dead there; stack use: one long.
Choice for the lead: `tc_clr` (exact, 1.9 k) or `tc_clrx` (4.3 k driving / 5.7 k standing, needs TC_GEOM in every state gate, proven unreadable but not state-identical).
