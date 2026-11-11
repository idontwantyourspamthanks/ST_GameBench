# Payload $1F00 -> $8000 (`$B3000-$BAFFF`): HD + floppy (2026-11-08)

Tools: `tools/mw2patch.py` (`PAYLOAD_LEN`, `build_runme`, `floppy_ffa`), runners `work/payload32k/run_hd.py`,
`run_floppy.py` (a copy of `work/floppy_tests/run_cell.py` with payload checks), `bp_runme.py`. Raw cell outputs:
`work/payload32k/h1..h6.out`, `f1.out`, `f2.out`, `bp_new.out`, `bp_old.out` (+ Hatari logs `*.hlog`).
Hatari 2.6.1. Everything below is from those outputs or from disassembly of `work/dumps/RUNME_unpacked.tos`; [INFERENCE] marks the rest.

## 1. Why the old limit existed, and the choice

`PC_FIXUPS = [0x98, 0x22E, 0xC24, 0x41EA, 0x41FC, 0x4514]` added N to a 16-bit word at `t+2`. A scan of the unpacked RUNME text
for every `d16(pc)` operand (`op & $3F == $3A`) whose target is >= the old bss start `$4536` gives exactly four real ones
(capstone, aligned decode):
```
0x98    lea.l $4756(pc), a1      (43fa 46bc)      0xc24   lea.l $4756(pc), a2   (45fa 3b30)
0x41ea  lea.l $4536(pc), a2      (45fa 034a)      0x41fc  lea.l $4536(pc), a1   (43fa 0338)
```
(plus `pea $4520(pc)` at `$ac6` and `pea $452b(pc)` at `$439c`, which point into the data segment and do not move; `$76c`, `$422a`,
`$43f2` match the mask but are data words.) The other two list entries are **not** pc-relative operands:
```
0x22a: 4eb9 0000 43d2 | 6006 ...   jsr $43d2.l  (0x22E = low word of the operand) ; 0x230 = bra.b $238 (6006 = "disp 24582")
0x4512: 6604  bne.b $4518 ; 0x4514: 45ea 0040  lea $40(a2),a2 ; 0x4518 dbra d3,$447a     (intro-picture plane loop)
```
The old build (`/tmp/RUNME_old_default.TOS`, md5 cf6ed481...) therefore wrote `7f20` over the `bra.b $238` word at text `$230` and
turned `lea $40(a2),a2` into `lea $1f5a(a2),a2` at `$4514` (bytes `45ea 1f5a`), while the new build leaves both as shipped.
Neither path runs on STE / Mega STE (`bp_new.out` / `bp_old.out`, 1 MB Mega STE TOS 2.06, text base `$149F2`, breakpoints counted to the
M/J/K screen): `$22A` 0 hits, `$230` 0, `$4476` (loop entry) 0, `$4514` 0, `$4518` 0, `$232` (`jsr $abe`, the other branch) 1 hit, same in both builds.
So the HD build's behaviour on those machines is unchanged; [INFERENCE] the old edit would have broken the d2 == 4 path (some other
machine type) and the plane loop.

All four real ones cannot reach bss any more for N = 32802 (`0x98`: 18108 + N > 32767, `0x41EA`: 842 + N > 32767), so the cap is not
one instruction but all of them. Options considered:
- **absolute `lea abs.l,aN` + reloc**: 6 bytes, the instructions are 4. No room (text slack is HAGA's runtime data area).
- **separate payload file loaded by the staging routine through GEMDOS**: the staging runs in PP's stack phase (own stack at `$B1F40`,
  interrupts masked, `$2700` set at the stub entry) after PP has taken over the machine; GEMDOS use there is unproven. Rejected.
- **payload behind the bss**: the loader reads only text+data from the file; bss is not file-backed. Not possible without a loader.
- **chosen: `lea d(pc),aN` -> `movea.l d(pc),aN`** (`227a`/`247a` + disp, same 4 bytes, same address register, no flags touched by
  either instruction) reading a **relocated pointer** from two longs (`$4550` = bss+`$220`+N, `$4554` = bss start+N) placed right behind
  the copy routine. They are two new reloc entries (the loader adds the TPA base); they lie within 32 KB of all four (`0x98` -> disp `$44B6`).
  Built RUNME, from `build/game/RUNME.TOS` text:
```
0x98    43fa46bc -> 227a44b6        0xc24   45fa3b30 -> 247a392a
0x41ea  45fa034a -> 247a0368        0x41fc  43fa0338 -> 227a0356
data: copy routine 41fa0020 43f9000b3000 303c1fff 22d8 51c8fffc 4ef90004d9a6 | ptrs 0000c778 0000c558 | image
header: text 17696, data 32824 (= 22 + N, N = 26 + 8 + $8000), bss 111206 ; reloc entries 63 -> 66 (+0x3aa staging jmp, +0x4550, +0x4554)
```
`build_runme` now asserts each site's original opcode/target, and **scans the whole text** for any other `d16(pc)` reference into bss
(`check_bss_pcrel_complete`), so a future change cannot silently miss one. Diff of the built RUNME text vs the unpacked original:
only the four leas, the +N on every relocated long that pointed into bss, the `$3A8` staging jmp and the `$754` tail jmp (script in
this session: "unclassified diffs vs ORIGINAL: []"; every relocated value == old + N).

## 2. Check 1: `$B3000-$BAFFF` stays free (1 MB and 4 MB; Mega STE TOS 2.06 and STE TOS 1.62)

Method (`run_hd.py`): a build of the default set + `test_blob16k` + a throwaway `zz_tmp_fill` (deleted) which fills the otherwise empty
`$B4F00-$B5FFF` and `$BA000-$BAFFF` with address-derived words, so the free parts of the range above the default blobs carry a pattern; the unused holes between the default blobs ($B3400-$B4EFF) are compared too (zero in the image, zero in RAM).
Cold boot; a debugger breakpoint at the boot stub `$4D9A6` (RUNME's `jmp` after the copy routine) dumps `$B2FF8-$BB000`; the same range is
dumped again at the M/J/K screen, at the HQ hall, at the map, at the 3D view and after a walk, and compared byte for byte with the image
`build_image()` produced. Raw lines (`h1.out`..`h4.out`):
```
cell                      stage (at $4D9A6)                 mjk         hall/map    3D view            after walk       MWPO  walk
Mega STE 2.06  1 MB (h1)  0 bytes differ                    3 differ    3 / 3       18 differ, 13 runs  19 differ       yes   moved
Mega STE 2.06  4 MB (h2)  0 bytes differ                    3           3 / 3       20 (15 runs)        19              yes   moved
STE 1.62       1 MB (h3)  0 bytes differ                    3           3 / 3       20 (15 runs)        19              yes   moved
STE 1.62       4 MB (h4)  0 bytes differ                    3           3 / 3       20 (15 runs)        18              yes   moved
```
Every differing run lies inside a declared `; data:` reservation ("outside declared data: []" in all 20 checks): `$B3402-3` (tick clock),
`$B42E2..$B42EE` (scheduler block `$B42E0+32`), `$B4681..$B4693` (HUD block), `$B46C1` (p5 data). `$B6000-$B9FFF == recognisable pattern: True`
and the fill words at `$BAFF0` (`f5aaf5a8...`) were intact at every checkpoint. At 4 MB the loader is in chunked mode (`pp_bigram_cache`,
`$81000-$B1D40`); without that patch the whole-image cache `$81000-$135000` would cover the payload (bigram.md).

**PP's stack-phase installer** (the copy README mentions at `$B1F44`), disassembly of RUNME text `$2fa-$3b4`:
```
2fc movea.l $5a0(pc),a1 ; 300 move.l $5a4(pc),d1 ; addq.l #1,d1 ; andi.b #$fe,d1 ; adda.l d1,a1     a1 = buf + len (even)
30c lea $200(a1),a1 ; 310 movea.l a1,a7 ; 314 lea $4(a7),a2                                              stack = buf+len+$200, dest = stack+4
318 lea $354(pc),a1 ; 31c movea.l a2,a3 ; 31e move.w #$243,d2 ; 322 move.l (a1)+,(a2)+ ; dbra            $244 longs = 2320 bytes
352 jmp (a3)
```
Chunked mode (`$5a0 = $81000`, `$5a4 = 200000`): a7 = `$81000+$30D40+$200` = `$B1F40`, copy = `$B1F44-$B2853`. Observed at the `$4D9A6` breakpoint in all four
cells: `A3 000B1F44  A7 000B1F40` (`h1.out`, `h2.out`, `h3.out`, `h4.out`) and the non-zero bytes of `$B1000-$B2FFF` are `$B1F44..$B2853` (Mega STE TOS 2.06,
1 MB and 4 MB) / `$B1F44..$B2851` (STE TOS 1.62). The installer copy and its stack end `$7AD` bytes below `$B3000`; the payload does not overlap it.
Whole-image mode (never active on 68000 with `pp_bigram_cache`; TT/Falcon only, buffer `$300100`) would put it at `$3B4304` [INFERENCE from the same code; no TT/Falcon TOS here].

Source/dest overlap of the copy itself: the appended data sits in RUNME's TPA at text base + `$4536...` ($149F2 on TOS 2.06, `$F176` on TOS 1.62, from `A0` at the breakpoint
minus `$C558`) and ends at `$20F4A` / `$1B6CE`, far below `$B3000`. [INFERENCE] a machine whose TPA starts above about `$A6000` (huge AUTO/ACC load) would overlap; the old limit was `$AC000`.

## 3. Check 2: floppy (FFA file 10)

- FFA track-sides (computed from `FILES/FFA`): `0-26 data, 27 zero, 28-71 data, 72-79 $F6 (blank), 80 data, 81-159 $F6`. The payload needs 8 track-sides = 72-79,
  exactly the free ones (the stub's loader reads linear track-sides; 80 holds data). `floppy_ffa` now aborts above that. The directory entry reads back
  `(10, 50071=cksum, 0, 72, 32768)`; the build self-check re-extracts file 10 through the directory and compares.
  There are no track-sides to spare in the 72-79 window (8 of 8 used; 4096 B of the last one unused), the limit is `$9000` bytes.
- Copy buffer: `f2.out`: `floppy copy descriptor $E550-$E56F: ffff 0000 0000 e566 0013 0004 a5d2 0015 0006 8000 ffff 0028 0008 0000 ffff 0000` = list pointer `$E566`,
  entry `[0028][00080000][ffff]`: 40 track-sides x 4608 B from `$80000` = `$AD000` (the original 80 = `$DA000`, floppy.md section 1), 24 KB below `$B3000`.
- In-game free region: in the 1 MB RAM dump at the 3D view `$B0000-$FFFFF` has 27741 non-zero bytes, 27737 inside `$B3000-$BAFFF` and 4 more = `MWPO` at `$B2FF8`
  (`f2.out`); nothing else is there (and floppy.md: unpatched floppy boot, same range all zero).
- Cold boot, patched floppy STE TOS 1.62 1 MB, payload compared at the M/J/K screen, hall, map, 3D view, after the walk: same table as above (3 / 3 / 3 / 3 / 21 bytes
  differing, all declared data), `MWPO`, pattern True, 3D `$6220=d $700a=2`, world rate 26.1 units/s (8 MHz), turn 0x300 -> 0x2c4.
- Default floppy (`work/floppy_tests/run_cell.py p32_fl_default_ste162 ste 162 1024 build/floppy 0`, `f1.out`): `MWPO`, `6220=d 700a=2`,
  `world_rate 8MHz ... units_per_sec 27.5`, heading `0x300 -> 0x2c6`. (Same values as work/notes/floppy.md T2 / regression.md for the previous build.)
- Not re-run: a full Start New Campaign disk copy (Hatari discards the campaign image writes, floppy.md section 4); only the buffer arithmetic above.

## 4. Check 3: default builds

`build/game` (RUNME md5 ea1d861b132d462acbc060fda27dc257): STE TOS 1.62 1 MB (`h5.out`) and Mega STE TOS 2.06 4 MB (`h6.out`): payload == image at the stub,
`MWPO`, 3D `$6220=d $700a=2`, walk moved, no byte differing outside declared data. 1 MB / 4 MB are also covered with the same default set + blob (h1..h4).

## 5. Check 4: `test_blob16k`

`patches/test_blob16k.s` (`default: no`): site `$2B4C0` (an existing `4e71` rewritten as `4e71`), blob `$B6000-$B9FFF`: signature `MW2-TEST-BLOB16K`, then word `i` = low 16 bits of its
own address. In the runs above `ram[$B6000..$B9FFF] == pattern` (computed independently in Python from the formula) is True at M/J/K, hall, map, 3D view and after the walk
on HD (4 cells) and on floppy (`f2.out`); head `b'MW2-TEST-BLOB16K\x60\x10\x60\x12...'`.
