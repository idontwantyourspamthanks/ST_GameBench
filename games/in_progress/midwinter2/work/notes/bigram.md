# >= 4 MB hang at the "Flames of Freedom" title: cause, fix, tests

Date 2026-11-08. Hatari 2.6.1, Mega STE TOS 2.06 (`tos/TOS_2_06.img`) unless stated. Fix: `patches/pp_bigram_cache.s`
(HAGA file patch, 2 bytes, `default: yes`). Raw logs: `work/bigram/*.out`, runner `work/bigram/run_cell.py`.

## Verdict
- The hang is **ours**, not the original game's: our payload at `$B3000-$B4EFF` is overwritten by PP's whole-image disk cache,
  which PP's HAGA init enables on >= 4 MB. The pristine game works at 4 MB (`mste206_4mb_pristine.out`).
  `work/regression.md` cell C/C0 blamed the original; its "unpatched" control `build/none` still has our RUNME staging.
- Fix = option (a), restricted to the case that collides: **68000 machines (ST, STE, Mega STE) with >= 4 MB keep PP's
  chunked cache** (the 1 MB / 2 MB behaviour). 68020+ machines (TT, Falcon) are untouched: their cache is at `$300100`.

## Evidence

### Pre-fix reproduction (`work/bigram/repro_nofix.py`, `build/none` = staging + 0 patches + original HAGA, Mega STE 4 MB)
```
M/J/K NOT reached after 14 polls (~100 s)
000B2FF8: 00 00 00 00                                      ....        <- 'MWPO' marker gone
000B3000: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................   <- payload gone
> b ($b3004).l ! ($b3004).l :trace
  $b3004 = $2c574          <- our staging copy (the displaced `move #$6002,$2c574` replay constant)
  $b3004 = $0              <- the big Fread
GEMDOS 0x3F Fread(64, 4096, 0x81000) at PC 0x14CB4
GEMDOS 0x3F Fread(64, 737280, 0x81000) at PC 0x3F910E
```
`$81000+737280 = $135000` covers `$B2FF8` and `$B3000-$B4EFF`. HAGA base on 4 MB is `$3F8000` (RUNME `$13a-$162`, see below).

### Where whole-image mode comes from (disassembly: `python3 tools/m68dis.py HAGA 0x3122 --end 0x3280`, RUNME via `work/dumps/RUNME_unpacked.tos`)
1. RUNME calls HAGA entry 13 (word `$3122` at HAGA+`$1a`; RUNME `$28a/$28e`, `a3=$80000`, `a4=$9c0(pc)`, `a0=$b4000`) and then copies the
   returned 10-byte record (`a0`, = HAGA+`$3274`) into its own stub data: RUNME `$292 move.l (a0)+,$5a0.l`, `$298 move.l (a0)+,$5a4.l`,
   `$29e move.w (a0),$5a8.l`. These text offsets `$5a0/$5a4/$5a8` are file offsets `$5bc/$5c0/$5c4` = low-RAM `$3C4/$3C8/$3CC`
   (the stub block is copied to `$200`: RAM = file - `$1F8`). `$000B4000` at file `$5b6` and `$27c` is the image-size constant.
   File default of the record (HAGA+`$3274`): `00081000 00030d40 0000` = {buf `$81000`, chunk 200000, flag 0}.
2. HAGA init, `$3218-$326e` (raw disassembly):
   ```
   003218: lea.l    $3274(pc), a2          ; record
   00321c: cmp.b    #$8, d1                ; d1 = HAGA+$87 = ST-RAM / 512 KB (2 = 1 MB, 4 = 2 MB, 8 = 4 MB, 16 = 8 MB, 28 = 14 MB; $196)
   003220: bcs.b    $3254                  ; < 4 MB: default record
   003222: move.b   $88(pc), d2            ; HAGA+$88 != 0 on a 68020+ ($280-$298: st.b)
   003226: bne.b    $3232
   003228: move.l   (a2), d2               ; 68000: buf = max($81000, a1)
   00322a: cmpa.l   d2, a1 ; ble.b $3238 ; move.l a1,(a2) ; bra.b $3238
   003232: move.l   #$300100, (a2)         ; 68020+: buf = $300100
   003238: move.l   a0, $4(a2)             ; chunk = $b4000 = whole image
   00323c: st.b     $8(a2)                 ; flag = $ff
   ...
   003254: move.b   $83(pc), d2 ; cmp.b #5,d2 ; bne $326e   ; TT only (HAGA+$83 == 5): {$180100, $5b8d8}
   00326e: lea.l    $3274(pc), a0 ; rts
   ```
   `a1 = a4 = $9c0(pc)` = RUNME's own data in its TPA: text base = `0x19148 - $4756` = `$149F2` in `pristine4_gemdos.txt` (HAGA is read with `pea $4756.l`, `Fread(64, 14000, 0x19148)`), so a1 = `$153B2` < `$81000` and buf = `$81000` (matches `Fread(..., 0x81000)`).
3. Stub (RUNME file `$474-$4ec`, RAM `$27C`), cache miss: `move.b $5c4(pc),d1 ; beq $4aa` (flag 0 = chunk path); flag != 0:
   `clr.l (a2); move.l $5b6(pc),4(a2)` (cache = [0, `$B4000`)), request {buf `[$5bc]`, seek 0, len `$B4000`}.
   Flag 0: request {buf, seek, len `[$5c0]` = 200000}, clamped at EOF (`$4c0-$4d4`).
4. RUNME `$318-$32c` also sets the stage-2 stack to `buf + len + $200` and copies its installer there (`$B1F44` in chunk mode
   = `$81000 + 200000 + $200 + 4`; `$135204` in whole-image mode). That is why `$B2FF8..$B3000` is untouched in chunk mode.
5. RAM size to HAGA base (RUNME `$13a-$162`): code < 4: `$F8000`; 4..7: `$1F8000`; >= 8: `$3F8000` (also 8 MB and 14 MB).

### Whole-image mode caches ONE image at a time (pristine, 4 MB, `--trace gemdos`, `work/bigram/pristine4_gemdos.txt`)
```
Fread(64, 4096, 0x81000)   at PC 0x14CB4    <- RUNME boot stub (FFA +512)
Fopen("FFA") at PC=0x3F9022  Fread(64, 737280, 0x81000) at PC 0x3F910E
Fopen("FFB")                 Fread(64, 737280, 0x81000)
Fopen("FFD")                 Fread(64, 737280, 0x81000)
Fopen("FFB")                 Fread(64, 737280, 0x81000)
Fopen("FFD")                 Fread(64, 737280, 0x81000)
Fopen("FFB")                 Fread(64, 737280, 0x81000)
```
There is a single descriptor `{start,end}` at `$3B6` (`$5ae(pc)`), reset to -1 when the image letter changes (RUNME `$3FA-$40A`)
and after every write (`$550-$55a`, `$592-$596`). So FFB/FFC/FFD are NOT cached together: each switch of disk re-reads the whole
image to the same `$81000-$135000`. The same chunked run after the fix (`fix4_gemdos.txt`): `Fread(64, 200000, 0x81000)` with seeks
9216, 211968, 414720, 537280 (= 737280 - 200000 clamp) for FFA, as on 1 MB.

### What PP's big-RAM mode was for [INFERENCE]
Speed. Every cache miss is one trip through the service (Fopen/Fseek/Fread/Fclose, low-memory and MFP swap, and in the original the grey
fade, README "while screen fades to gray and back multiple time"). Whole-image mode needs 1 miss per disk switch instead of one per 200 KB
window. Measured below: 6 service calls to the 3D view instead of 56.

## Fix (options considered)
- (a) chosen: 2 bytes. HAGA+`$3228` `2412` (`move.l (a2),d2`) -> `602a` (`bra.b $3254`). 68000 machines >= 4 MB skip the
  whole-image block and take the < 4 MB path (`$3254`: `HAGA+$83 != 5`, so it ends at `$326e` with the default record). No other byte changes; `$322a-$3237` become dead.
  The tool verified the original bytes against the file and the RAM dump and that the new bytes assemble identically at both HAGA bases;
  the branch is pc-relative, so `$3F8000` (4/8/14 MB) works too (tested).
  A cheaper-looking `cmp.b #8,d1` -> `cmp.b #$ff,d1` would also change TT/Falcon (they would lose their `$300100` cache), so it was not used.
- (b) a payload address free in all RAM sizes and both modes: not available. The game occupies `$400-$B2851`; `$B2852-$E83E5` is the
  only free hole on 1 MB, and PP's whole-image cache starts at `$81000`. An alternative would be to relocate PP's buffer
  (`move.l a1,(a2)` -> buf = `$100000` on 68000, plus the stack at `buf+len+$200`), which would keep the speed. NOT done:
  it needs proof that nothing of PP's low-memory save area/stack (`$8100..` below `top - 512 KB`) overlaps at 4/8/14 MB. [INFERENCE: feasible]
- (c) re-copy the payload after the big read: rejected. The Fread zeroes `$B2FF8-$B4EFF` while the trampoline/hooks may be
  live, execution later returns into the payload (lead's trace: `rte` to `$B3210`), and every later whole-image miss (FFB/FFD switches, 5 in the trace
  above) would need the re-copy again, with no hook point in PP's service. [INFERENCE: fragile]

## Tests (all with `build/game` = default set incl. `pp_nofade` + `pp_bigram_cache`)
Procedure (`work/bigram/run_cell.py`): cold boot, `boot_to_game('M')` logic, `$6220==$d && $700a==2`, `m $b2ff8 4`, `savebin` of
`$B3000-$B4EFF` compared with the built payload (`work/bigram/payload.img` = `mw2patch.py live` image; first `$400` bytes = trampoline,
load hook, applier, site table), then `rel(0,-200); center(); rel(0,-200)`, 12 s, `$66e6/$66ea/$6888` before/after.
"payload differs" bytes are all runtime data (tick clock `$B3402`, scheduler block `$B42E2..`, HUD data `$B4681..`), never zeros.

| Cell | 3D view | MWPO | `$B3000-$B33FF` == image | walk |
|---|---|---|---|---|
| Mega STE TOS 2.06, 1 MB | yes | MWPO | True (19 data bytes differ) | moved |
| Mega STE TOS 2.06, 2 MB | yes | MWPO | True (19) | moved |
| Mega STE TOS 2.06, 4 MB | yes | MWPO | True (21) | moved |
| Mega STE TOS 2.06, 8 MB | yes | MWPO | True (19) | moved |
| Mega STE TOS 2.06, 14 MB | yes | MWPO | True (20) | moved |
| STE TOS 1.62, 4 MB | yes | MWPO | True (20) | moved |
| Mega ST TOS 1.04 (`--machine st`), 4 MB | yes | MWPO | True (20) | moved |
| pristine Mega STE 2.06, 4 MB | yes | n/a (no staging) | n/a | moved |
| pristine Mega STE 2.06, 1 MB | yes | n/a | n/a | moved |

Raw lines of the 4 MB Mega STE cell (`mste206_4mb_fix.out`):
```
3D view: $6220=d $700a=2
MWPO check: 000B2FF8: 4d 57 50 4f                                      MWPO
payload $B3000..$B33FF equals built image: True | whole $1F00: 21 bytes differ (runtime data areas)
$B3000 first 16 bytes: 33fc60020002c57448e7fffe40e723fc  image: 33fc60020002c57448e7fffe40e723fc
walk start (x,y,dist): ['0x6400', '0x6400', '0x4f8']  after 12 s: ['0x5c7a', '0x6400', '0x386'] moved
```
Pre-fix control in the same cell shape (`mste206_4mb_pristine.out` is the original game, no staging): `$B3000` holds cache data there
(`83145b14f0f0e02b...`), as expected, and the game does not care.

## Load time in whole-image vs chunked mode (4 MB Mega STE; VBL at 50 Hz)
Measured by breakpoints on the HAGA service entry (`HB+$fc4`) and its `rts` (`HB+$1164`), logging `e VBL` at each (`work/bigram/svc_time.py`).
Time between the first service call and the M/J/K screen is dominated by the harness' space-key schedule, so the screen-match VBLs
(polled every 5 s) are only coarse.

| Build, 4 MB | calls / service VBL until M/J/K | calls / service VBL until 3D view | M/J/K screen VBL (poll) minus intro-loop start |
|---|---|---|---|
| pristine (whole image) | 2 / 54 | 6 / 194 | 1576 |
| staging + `pp_bigram_cache` only | 11 / 361 | 56 / 1816 | 1883 |
| **default build** (`pp_nofade` + `pp_bigram_cache`) | 11 / 127 | 56 / 639 | 1577 |
| pristine at 1 MB (chunked, the same path) | 11 / 394 | 56 / 1984 | 1883 |

- Forcing chunked reads costs +307 VBL (+6.1 s) before the M/J/K screen and +1622 VBL (+32 s) to the 3D view when nothing else is changed
  (361 vs 54, 1816 vs 194): the same as 1 MB machines.
- In the default build `pp_nofade` removes the fades from each call (max call 12 VBL vs 39-42), so it ends at +73 VBL (+1.5 s) to
  M/J/K and +445 VBL (+8.9 s) to the 3D view vs the original at 4 MB. That is still faster than the original at 1 MB (1984 VBL).

## Not tested
- TT/Falcon with >= 4 MB ST-RAM (no TT/Falcon Atari TOS; EmuTOS tests in `regression.md` are 1 MB). Their branch is not touched by the patch.
- Hardware: the user's MiSTer Mega STE (4 MB). Hatari megaste with TOS 2.06 at 4 MB passes.

## Reproduce
- "fix only" build: `python3 tools/mw2patch.py build --only pp_bigram_cache --out build/bigram_only` (+ copy `work/disk_overlay` into its `work/`); pristine = the original root files plus `work/disk_overlay`.
- Cells: `python3 work/bigram/run_cell.py NAME MACHINE TOS MEM_KB GAME_DIR [timing]` (`batch.sh` lists the ones run); service VBLs: `python3 work/bigram/svc_time.py CELL...`; GEMDOS traces: `trace_run.py`; pre-fix repro: `repro_nofix.py build/none`; zip: `make_zip.py`.
