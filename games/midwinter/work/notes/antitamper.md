# Midwinter 1 (PP HAGA HD build) — the anti-tamper checksums, other integrity checks, and how our patches coexist

Read-only analysis plus live RAM experiments (nothing in the repo was patched). 1 MB STE, TOS 1.62, Hatari 2.6.1.
Dumps: `work/dumps/ram_ski_walk.bin` (ski view), `work/dumps/ram1mb_options.bin` (Game Options screen, unpatched boot).
Snapshots: `1mb_ski_stand` / `1mb_ski_walk`. Profiles: `work/prof/{walk,stand}.txt`. Disassembly = `tools/m68dis.py`
(`<dump> <addr> --end <addr>`). RUNME/PP facts are from `loading.md` (section 4). Anything not proven is marked [INFERENCE].
My scratch scripts lived in `/tmp` (`exp.py`, `t1.py`, `e5.py`, `e6.py`); raw outputs are pasted below.

## TL;DR

| Question | Answer |
|---|---|
| What is checked | A byte-sum of **3D object model data**, loaded from MWA file 6 (dest `$3167C`, `$C40E` bytes). Global block `[$31698,$3DDB4)` (50972 B) and 30 per-object ranges (43088 B). **No code is covered.** |
| When | (a) **Global** sum `sub_01235c`: at 5 screen/mode transitions (`$3126 $58F0 $FC0C $12526 $12616`). (b) **Per object**, `sub_0122f0`: first instruction of `sub_01dd14` (the 3D renderer's object set-up), once per object drawn: **1-2 times per frame in the ski view**. |
| Expected values | **Computed at load, not hard-coded.** The file holds zeros in the table, the global sum and the range words. Object table built at boot by `$1ed6e`; global sum at `$C16-$C44`. Static in this build: global `$25824D` (same in the Options-screen dump and the ski dump). |
| On mismatch | **Infinite loop with the palette register `$FF8240` stepping** (no message: the debug-print entry `$E454` is a bare `rts` in the original file). PC stays in `$12318-$12320`, `$1234C-$12354` or `$12384-$1238C`. |
| Other checks | Only one more *checksum*: the per-file XOR of the game's own disk loader (`$10D78`). Plus PP-neutralised protection (the FVPF manual check `$12050`, FDC/seek stubs) and a dead unreferenced sum routine (`$2840`). No other sum loop, no code that reads its own text (scans below). |
| PP's 12 patches | All lie at `$64D2-$12050`, i.e. in resident **code**, below `$31698`. Not covered, and applied before any sum exists. |
| Cost | The per-object loop `$12288-$12292` is **2.81 % (walk) / 7.29 % (stand)** of profiled cycles. Removing it: **80 -> 86 flips/1000 VBL standing (measured)**. |
| Recommendation | Our patches target resident code, so they need **no action**. For data in the covered block, patch at the file-6 load hook (sums then include the edit). To get the speed-up and freedom: two 2-byte boot patches `4e75` at `$122F0` and `$1235C` (verified live, below). |

## 1. The mechanism (disassembly)

### 1.1 The summing primitive
```
sub_012276:                         ; sum of bytes [ [$12390], [$12394] ) -> [$12398]
012276: movem.l d0-d2/a0,-(a7)
01227a: moveq #0,d1
01227c: movea.l $12390.l,a0
012282: move.l  $12394.l,d0
012288: cmp.l   a0,d0
01228a: beq.b   $12294
01228c: moveq   #0,d2
01228e: move.b  (a0)+,d2
012290: add.l   d2,d1
012292: bra.b   $12288
012294: move.l  d1,$12398.l
```
Plain 32-bit sum of unsigned bytes, 6 instructions per byte (profile: `$12292` bra = 10 cycles/byte).

### 1.2 Setting up the expected values (all at runtime)
File bytes `$12390-$12513` of the game (MWA sector 195 + `(addr-$7E4)`) are zero except `$123A8 = 000123ac` (checked in Python:
"nonzero 3, `$123a8: 000123ac`"). Everything else is filled during game start-up. Initialisation routine `sub_00b7e`..`$c06`:
```
000b7e: lea.l $2c376.l,a6 ; ...
000b8c: jsr $100e2.l
000b92: jsr $1050e.l           ; load MWA file 6 -> $3167C, then relocate the 30-long pointer table:
                               ;   01052c lea $31698,a0 / move.l a0,d0 / move.w #$1d,d1 / 010538 add.l d0,(a0)+ / dbra
000b98: jsr $1ed6e.l           ; per-object processing + record (below)
000b9e: jsr $10544.l           ; loads MWA files 3,1,4,5,2
...
000c10: jsr $11c7e.l           ; FVPF manual check page (PP: $12050 = rts, section 3)
000c16: move.l #$31698,$12390.l
000c20: move.l #$3ddb4,$12394.l
000c2a: jsr $12276.l           ; global sum of [$31698,$3DDB4)
000c30: move.l $12390.l,$1239c.l      ; start
000c3a: move.l $12394.l,$123a0.l      ; end
000c44: move.l $12398.l,$123a4.l      ; expected global sum (= $25824D in this build)
```
Per-object table: `sub_01ed6e` loops 30 times over the pointer table:
```
01ed6e: movem.l d0/a0-a1,-(a7)
01ed72: lea.l   $31698.l,a0 ; 01ed78: move.w #$1d,d0
01ed7c: move.l  (a0)+,$1ef96.l         ; object pointer
01ed82: bsr.w   $1ed96                 ; process the object in place (relocation, edge lists; ends with 01ef28 move.l a1,$12394)
01ed86: jsr     $122a0.l               ; sub_0122a0: record
01ed8c: dbra    d0,$1ed7c
sub_0122a0:                            ; (both branches of tst.w d0 are identical)
0122a8: move.l -$4(a0),$12390.l        ; start = pointer just read
0122b0: jsr    $12276.l                ; sum [start, end set by sub_01ed96)
0122b6: movea.l $123a8.l,a1            ; table write pointer (initial $123ac)
0122d2: move.l $12390.l,(a1)+ ; 0122d8: move.l $12394.l,(a1)+ ; 0122de: move.l $12398.l,(a1)+
0122e4: move.l a1,$123a8.l
```
So the table at `$123AC` has 30 entries of 12 bytes `{start.l, end.l, sum.l}` (30 x 12 = `$168`, ending at `$12514`, which is
where the next code, `sub_012514`, begins; `$123a8 = $12514` in the dumps after the build). The sums are taken **after** `sub_01ed96`
has processed the object in place (it does `add.w d1,0(a0)`, `divu.w #6`, compaction `move.w (a0)+,(a1)+` ... `01ee9e-01ef28`), so they
cover the processed, resident form. Order of the table == order of the pointer table at `$31698`.

Measured at runtime (cold boot, `b pc = $10d6c / $b98 / $c16 / $c2a :trace`, `m $2c4d2 2` at the load exit; raw, T1):
```
10d6c file 06 | b98 | 10d6c 03,01,04,05,02 (MWA) 2f,1e,1f,21 (MWB 47,30,31,33) | c16 | c2a | 10d6c 24,30 (MWB 36,48)
$123a4 0025824e (T1, one byte +1 written at the file-6 hook)   $1239c 000316980003ddb4
```
(ordering matters for patching, section 5). The global sum is taken after all MWA files and MWB 47/30/31/33, before MWB 36 and 48,
none of which land inside `[$31698,$3DDB4)` (dests `$404C4 $4F1E0 $52196 $53BF0 $7A000 $2A14C`, `loading.md` section 3.3).

### 1.3 The two verifiers
```
sub_0122f0 (per object, a4 = object start):                  sub_01235c (global):
0122f4: move.l a4,d1                                         01235c: move.l $1239c.l,$12390.l
0122f6: lea.l $123ac.l,a0 ; moveq #$1d,d0                    012366: move.l $123a0.l,$12394.l
0122fe: cmp.l (a0),d1 ; beq $12322 ; adda.l #$c,a0 ; dbra    012370: jsr $12276.l
01230c: .. not found: moveq #0,d0/d1 ; move.l a4,d2          012376: move.l $12398.l,d0
012312: jsr $e454.l   ; 00e454: rts  (original bytes)        01237c: cmp.l $123a4.l,d0 ; beq $1238e
012318: addi.w #$100,$ff8240.l ; 012320: bra.b $12318         012384: addi.w #$100,$ff8240.l ; 01238c: bra.b $12384
012322: move.l (a0),$12390 ; move.l 4(a0),$12394             01238e: rts
012330: bsr.w $12276 ; 012334 move.l $12398,d0
01233a: cmp.l 8(a0),d0 ; beq $12356
012340: moveq 0,d0/d1 ; move.l a4,d2 ; jsr $e454 ; 01234c: addi.w #$1,$ff8240.l ; 012354: bra.b $1234c
012356: movem.l (a7)+,.. ; rts
```
Callers: `$122f0` has one caller, `$1dd18` in `sub_01dd14` (object set-up, 4 callers `$4484 $11a22 $1d638 $1d706`;
`$1d638/$1d706` load `a4` from `$1d81c`). `$1235c` has 5 `jsr` callers: `$3126` (in the routine that follows `$310c`), `$58F0` (`sub_0058c0`),
`$FC0C` (`sub_00fbe0`), `$12526` (`sub_012514`) and `$12616` (end of `sub_0125a0`, right after `jsr $1498a` returns from the action mode).
(Byte-pattern search for `0001235c` in `$0-$50000` finds exactly these five; `m68dis --callers` misses `$3126` because it scans from `$4000`.)

Three different hang signatures: unknown object key `$12318` (step `$100`); per-object sum mismatch `$1234C` (step `$1`, i.e. a slow blue
ramp); global mismatch `$12384` (step `$100`). `jsr $e454` is a no-op in the shipped file (`image 4e75` at `$E454`, matching the dump), so
no text appears; the screen just freezes with the palette colour 0 cycling (VBL still runs, nothing re-checks).

### 1.4 What the ranges are
Per-object ranges (from the dump table; `sum` is the expected word the loader computed, all 30 verified equal to a fresh sum of RAM):
```
 0 $337f0-$33aa8 $06d7f | 1 $36d60-$373aa $12fd4 | 2 $374cc-$37784 $07e6b | 3 $3250e-$32eba $1f9ba | 4 $31710-$31b88 $0e07b
 5 $34f1c-$3524e $085fa | 6 $31c32-$31f46 $08856 | 7 $3422c-$346f8 $0e1c6 | 8 $33f34-$341c4 $072ab | 9 $33b10-$33eae $0a915
10 $357a4-$35e7c $15bbb |11 $347b4-$34e12 $145ee |12 $36394-$36c10 $1c28f |13 $31fbc-$32458 $0e106 |14 $35faa-$36308 $097f0
15 $33044-$336bc $140ad |16 $377f6-$37ac8 $0822c |17 $352d0-$356f0 $0d158 |18 $3a7aa-$3b228 $22724 |19 $38c42-$39252 $13736
20 $39342-$39a56 $15f3e |21 $39b82-$3a5f4 $201b6 |22 $384ae-$38b42 $14708 |23 $37b32-$3835e $18c34 |24 $3b3de-$3ba08 $139e6
25 $3bafe-$3c008 $0d29f |26 $3c0d4-$3c832 $1a25e |27 $3c96e-$3ce4a $10666 |28 $3cf0e-$3d312 $0bcaf |29 $3d3be-$3d994 $13768
```
(`[start,end)`; python check "block sum 0x25824d stored 0x25824d, bad 0".) The global block is `[$31698,$3DDB4)`: the 120-byte pointer
table, the 30 ranges (43088 B), and 7884 B between/after them (the un-compacted tail of each object, plus `$3D994-$3DDB4`, which
is zero beyond `$3DA8A`). The per-object ranges leave those 7884 B unchecked per object, but the global sum covers them. The first 28
header bytes of file 6 (`$3167C-$31697`) and everything outside `[$31698,$3DDB4)` are not covered by anything.
[INFERENCE] the 30 objects are the 3D models (header words = vertex/edge/face counts, `sub_01ed96`); the object drawn in the ski view
is `$352D0` (1056 B, one hit/frame in `1mb_ski_walk`) and, in `1mb_ski_stand`, `$352D0` plus `$37B32` (2092 B): 19 hits each in 250 VBL
and 19 flips (raw `e6.py`: `Counter({'00037B32': 19, '000352D0': 19})`, `flip routine hits 19`).

### 1.5 Frequency and cost
Profile lines of `sub_012276`/`sub_0122f0`/`sub_01235c` (range `$12276-$12390`, sum of the cycles column over the whole file):
```
walk : 992264 of 35267684 cycles = 2.81 %   (the loop $12288-$12292 alone: 240884+200946+160624+160576+120498+80312)
stand: 2574272 of 35330544 cycles = 7.29 %
```
All profiled cycles in both files lie below `$31698` (resident code). ~35 cycles per byte (profile) x 1056..3148 B per frame.

## 2. Other integrity checks in the resident code

Method: (1) disassembled `$7E4-$2DD32` linearly and listed every backward-branch loop whose body reads memory through `(aN)+` and accumulates
into a data register with `add/eor/sub` (script `/tmp/scan.py`, `/tmp/scan2.py` which also accepts indexed sources); (2) listed
every `lea`/`move` of a resident-code address into an address register followed within 9 instructions by a backward branch
(`/tmp/scan3.py`, 139 hits, all data tables/strings/screens, none a code read); (3) same loop scan on the stub `$CFE4-$E1E3`, stage-2
`$3DF28-$50655`, the low stub `$200-$5E7` and the overlays `$31698-$80000`. Results:

| # | Where | What | Protects | Status in the HD build |
|---|---|---|---|---|
| 1 | `$12276`, `$122a0`, `$122f0`, `$1235c`, `$1ed6e` | byte sums (sections 1.1-1.4) | MWA file 6 objects `$31698-$3DDB4` | **active** |
| 2 | `sub_010d78` (`$10D78-$10DA6`): `eor.w d2,d0` over the loaded file's words vs `$8(entry)` of the directory table at `$258A6`/`$2590C` | XOR16 of every file read by `sub_010cd2` | file contents as loaded from disk | active; mismatch -> `sub_010da8` (calls `$E454` = rts) then `sub_010db8` shows "Insert graphics disk / Press any key" and waits for a key, then `bra $10cf4` re-reads. Loop, not a hang. 51/51 MWB entries match the raw image (`loading.md` 3.2) |
| 3 | `sub_012050`, the FVPF "SECURITY CHECK" (manual, `$11D7E`) | click-the-name quiz | the user | PP's patch `$12050 <- rts` (`loading.md` 4); floppy build has the real quiz (`patches/floppy_secbypass.s`) |
| 4 | `$1102E`, `$11344` (FDC seek, drive select), `$D406`/`$D18C` (stub), stage-2 `$3ED06/$3ED98/$3EF8E/$3E1AC`, low-RAM hooks | disk-level protection / loader | the floppy | PP replaced them with `rts`/hooks (`loading.md` 2, 4). Not RAM checks |
| 5 | `$2840-$2856` `add.l (a0)+,d1` over 24 longs at `$24FC8` -> `$24FC4` | sum of a jump table (`$24FC8` = 24 handler pointers, dispatched at `$15A0 jmp (a0)`) | handler table | **dead**: no `jsr/bsr/jmp` to `$2840-$284A` in `$7E4-$2DD32` (python scan), no 32-bit literal `00002840`, `$24FC4` is read nowhere (`xref` shows only the write `$2850`), `$24fc4 = 00000000` in the dump |
| 6 | Boot sector sum `$1234` (MWA) | TOS bootable check | floppy only | unchanged (`floppy.md`) |
| 7 | Stage-2/stub table 4th word (`$A42E`, `$7455`..) | XOR16 words | stage-2/game images | **unused** by stub and stage-2 (`floppy.md` line 31) |
| 8 | RUNME `$A2-$C8` | `a1 < $38270` sanity check of HAGA buffer address | RUNME's own layout | passes with our 32 KB growth (`loading.md` 7) |

The other hits of the loop scan are not checks: `$2B34-$2B96` bit-plane interleave, `$285A-$28FA` colour mixing (`eor.w d5,d4`),
`$A278/$A95E/$AA88` text width, `$BE32-$BF06` and `$3E546` pointer relocation (`add.l d1,d0 / move.l d0,(a1)+`), `$D3B0` score sum,
`$DCE2` RLE depack, `$1E8C4` edge lists, `$ECA0` per-entity ($2B194 records) update. [INFERENCE] The scan is static and linear: a check built from
unrolled code, a different register shape or a computed jump could be missed. The profile corroborates the dynamic picture:
in 250 VBL of walking/standing the only memory-summing loop with a measurable cost is `$12288-$12292`.

## 3. Live experiments (snapshot `1mb_ski_stand`; writes via the Hatari debugger `w`)

Status line = flips per 60 VBL, `$FF8240` (3 samples), `$1EFDE` (0 = ski loop, 1 = menus), PCs. After the write the
snapshot runs; "X" = `h.exit_action()` (back to Decisions, goes through `$12616`/`$1235c`).

| Exp | Write | Result (raw) |
|---|---|---|
| A (control) | resident **code**, dead `sub_002840` `41f9 -> 4e75` | `[after write] flips=4 $ff8240=0000 $1efde=0`; X: `bp hits: $12616 x1, $1235c x1, $1235c x2`, then `$1efde=1 PCs 0000bd06` (menu wait loop). **No effect**; the global check ran and passed |
| B | `$3DDB0: 00 -> 01` (inside `[$31698,$3DDB4)`, outside every object range) | ski loop unaffected (`flips=4`, palette `0000`). After X: `$12616 x1, $1235c x1`, `$ff8240=['0e00','0b00','0700'] PCs=['000065b4','0001238c','0001238c']`: **global check hangs**, step `$100` |
| C | `$356EF: 04 -> 05` (last byte of the drawn object `$352D0-$356F0`) | `[after write] flips/60VBL=0 $ff8240=['0cd8','0d4e','0dc4'] PCs=['00012354','0001234c','0001234c']`: **hangs within one frame**, in the per-object loop, step `$1` |
| D1 (non-atomic) | C, then fix `$12480` (entry 17 sum) and `$123A4` 0.5 s later | still hung (`$12354`): the hang is permanent, the table must be right *before* the next frame |
| D | one command file at `b pc = $122f0 :trace :once :file`: `w $356ef $05; w $12480 $00 $00 $d1 $59; w $123a4 $00 $25 $82 $4e` | `bytes 05 0000d159 0025824e`; `flips=4 $ff8240=0000 $1efde=0`; X: `$12616 x1, $1235c x1, x2`; `$1efde=1`, `PCs 0000690a 0000bd06`. **Stored sums updated atomically -> no trip** |
| F | `$12478: 000352d0 -> 00000000` (drop the table key of the drawn object) | `$ff8240=['0000','0600','0c00'] PCs 00012320/00012318`: **hangs in the table-miss loop**, step `$100` |
| E | `4e75` at `$122F0` and `$1235C`, then `$356EF +1` with no sum update | `fps(1000 VBL)`: baseline `{'flips': 80, 'vbls_per_frame': 12.5}`, patched `{'flips': 86, 'vbls_per_frame': 11.63}`; `[patched ski loop] flips/60VBL=5 $ff8240=0000 $1efde=0`; X: `$1efde=1 PCs 0000bd18`. **No hang**, +7.5 % frames when standing |

Cold-boot experiments (one byte at `$3DDB0` inside the covered block, written by a debugger command file at a conditional breakpoint
`b pc = $10d6c && ($2c4d2).w = N :trace :file`, `$2c4d2` = file number of the load that just finished; raw):

| Exp | When written | Result |
|---|---|---|
| T1 | at the exit of the **file 6** load (before `$B98`/`$C2A`) | `$123a4 = 0025824e` (**the byte is part of the expected sum**). Options -> PLAY -> Stark -> Decisions -> Skiing all pass (`$1235c` hit once at Decisions and once at Skiing), `$1efde=0` in the ski view, X returns to Decisions (`$1efde=1`). **No trip** |
| T2 | at the exit of the **file 48** load (after `$C2A`) | `$123a4 = 0025824d` (stale). Options, The Team and Stark load fine (`$1235c` not yet called). The first `$1235c` call, on the Stark -> Decisions transition, hangs: `after DECISIONS: $1235c hits=1 PC=['000068fa','0001238c'] pal=0100`, still `PC=['00012384','0001238c'] pal=0e00` after clicking Skiing: **hang** |

So the protection is a *self-consistency* check: the reference sums come from the data as it is when the game starts, so what the loaded
bytes are before `$B98` (per-object) and `$C2A` (global) is irrelevant; changes after that are what trip it.

## 4. Why PP's HD patcher does not trip it
- Its 12 game patches (`loading.md` 4) are at `$64D2 $1011E $10172 $101C6 $1024A $10E5C $10F86 $110FE $111A6 $1102E $11344 $12050`, all in the resident
  code at or below `$12050`, which is below the covered block `$31698-$3DDB4`. Nothing checks code (section 2).
- Experiment A shows a write into resident code passes the global check and the per-frame check.
- Timing is also fine: PP's block C runs after stage-2 has loaded the game and before `jmp $800`, so even a write into a covered
  range would have preceded the `$C16-$C44` sum (T1).
- Our own staging (`$B3000-$BAFFF`), the trampoline hook at `$10D6C` (`33df000062b8 -> jmp $B3070.l`) and the HAGA file patches are outside
  `[$31698,$3DDB4)`. The deferred applier runs right after the checksum `$10D78`, so it also sits before file 6's sums are taken when it patches file 6.

## 5. Recommendations

1. **Default: no action.** Every hot function is resident code below `$31698` (both profiles: 100 % of cycles below `$31698`). Any patch whose
   sites lie in `$7E4-$2DD32` (and our payload in `$B3000+`) is invisible to every check, boot-phase or deferred.
2. **Never write to `$31698-$3DDB4` after `$C2A` unless you also fix the sums** (or neutralise the checks). Covered range = all 30 objects
   and their unchecked tails alike (the global sum covers the tails). A single changed byte hangs the game at the next object draw (inside the ski
   view) or at the next transition.
3. **If object data must change, edit it at the exit of the file-6 load** (the existing deferred hook at `$10D6C`, `; load: MWA 6 $3167c`, file
   number `$2C4D2 = 6`): T1 shows the sums then include the edit. Remember that at that moment the data is the raw file; relocation
   (`$10538`) and `sub_01ed96` run afterwards, so write the *file* format. If the change is wanted in the processed form, the alternative is to patch after `$B98`
   and update **both** the entry's sum in `$123AC + 12*i + 8` and the global sum `$123A4` in the same atomic step (Exp D; both must be consistent
   before the next frame).
4. **Optional speed-up that also removes the constraint** (verified in Exp E, 7.5 % more frames standing, ~2.8 % walking): two boot-phase 2-byte patches, both in the
   resident game, both verified `orig` in image and in `ram1mb_options.bin`:
   ```
   ; name: mw1_nocheck_obj      ; site: $122f0   ; orig: 48e7   -> new: 4e75     (rts instead of movem.l d0-d7/a0-a6,-(a7))
   ; name: mw1_nocheck_global   ; site: $1235c   ; orig: 23f9   -> new: 4e75     (rts instead of move.l $1239c.l,$12390.l)
   ```
   `$122f0` has a single caller (`$1dd18`, `jsr`), `$1235c` five `jsr` callers; both are plain subroutines, the callers do not use their flags or
   registers afterwards (`01dd1e: move.w $0(a4),d0` reloads everything). With both in place a covered byte can be changed freely
   (Exp E wrote `$356EF` +1 with no sum update; no hang in the ski loop or at X). Optional extra (boot time only, ~43 KB x ~35 cycles = ~1.5 M cycles, ~0.2 s at 8 MHz, [INFERENCE] estimate): `4eb9 000122a0` at `$1ED86` ->
   `4e71 4e71 4e71` (skip recording the table; do NOT touch `jsr $1ed96`, it processes the objects). Not needed.
   Do not patch `$12276` itself: it is the shared summing primitive and the `$12398` result must stay consistent with whichever verifier still runs.
5. Floppy build: same game code, same checks, nothing to add; the only difference is the real FVPF quiz (`floppy_secbypass`).
6. Disk images: if any file that the game loads through `sub_010cd2` is ever modified on the image instead of in RAM, update its XOR16 word in the
   directory table (`$258A6`/`$2590C`, `loading.md` 3.1) or the loader retries forever with "Insert graphics disk". The RAM hook runs after that check, so RAM patches are unaffected.

## 6. Open points / caveats
- [INFERENCE] The intended threat model (trainer/cheat protection against memory-resident edits, since the reference is taken at runtime) is not documented; what is
  proven is the mechanism and the behaviour above.
- The stage-2 and boot-stub code was only scanned for sum loops, not read end to end; `loading.md` documents their PP patches.
- Experiments were on a 1 MB STE; the checks are in game code, so the TT/Falcon/4 MB paths are expected to behave the same but were not run.
- The mismatch screen has no text because `$E454` is `rts` in the shipped game: a patched build that hangs here will look like a plain frozen, colour-cycling screen.
