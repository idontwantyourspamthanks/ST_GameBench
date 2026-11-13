# Hunter triple buffering and the v1.2 RAM map (HunterTriple)

Tags: **[obs]** observed in Hatari 2.6.1 (raw output quoted), **[disasm]** from `work/dumps/ram_foot_stand.bin`
(`tools/m68dis.py`), **[INFERENCE]** not verified.

Patches: `patches/tb_flip.s` (site `$5fd2`, carries the code and the state block), `tb_frame.s` (site `$5fc2`),
`tb_vbl.s` (site `$c600`); gate-only helper `patches/test_tblock.s` (site `$5fa4`, never in the release).
Tools: `tools/hunttb.py` (free-RAM pattern proof, HD and floppy cells), `tools/hunttb_ab.py` (per-frame picture gate).
Prefix windows: `tb_` `$8C1B2-$8C3FF` in `huntpatch.py PREFIX_RANGES`.

## 1. The original flip (what is being changed)

```
005fc2: 610e            bsr.b  $5fd2        ; flip
005fc4: 61004adc        bsr.w  $aaa2        ; wait for the next VBL (the "flip wait")
005fc8: 60da            bra.b  $5fa4        ; latch: $1ac(a5) = $1aa(a5); $1aa = 0
005fd2: 203a1f98        move.l $7f6c(pc),d0 ; A = $23000
005fd6: 223a1f9c        move.l $7f74(pc),d1 ; B = $2ad00
005fda: 086d0002008f    bchg.b #2,$8f(a5)   ; toggle
005fe0: 6702            beq.b  $5fe4
005fe2: c141            exg.l  d0,d1
005fe4: 2b400144        move.l d0,$144(a5)  ; draw page
005fe8: 2b410148        move.l d1,$148(a5)  ; shown page
005fec: e049            lsr.w  #8,d1        ; base = $148 into $ff8203 / $ff8201
```
[disasm] Two 32 000-byte pages, `$144(a5)` = the page the pass draws into, `$148(a5)` = the page the shifter shows.
`$aaa2` is the wait that costs 2.5-9.5 % of every frame (`hotpaths.md` stage `$5f6a`).

The pointer (`$a65c`, called from the VBL handler at `$c69a` when `$1ce(a5)` bit 7 is set) restores the 9 saved
pointer rows at the address it saved, then redraws the pointer into the page the video base points at [disasm
`$a65c..$a718`]. That is why the flip is followed by a VBL wait: the pass must not draw into the page that still
holds the pointer until the VBL handler has restored it.

## 2. Free RAM, proved (pattern method)

Pattern: `huntpatch.fill_byte(a)` (never 0), loaded with `loadbin` at **`pc = $800`** (the game entry; the patched
START stub jumps there directly, so `$80154` is never reached - the first attempt of this session measured nothing
because of that), then the game is played and RAM dumped and compared (`tools/hunttb.py`).

| cell | regions filled | result |
|---|---|---|
| HD STE 1.62 1 MB, boot + 30 s Up+Left driving + drone map + game options + disk options + re-brief | `$81000-$8B9FF`, `$32A00-$3682B`, `$B8200-$BFFFF` | **0 of 91692 changed** |
| HD ST 1.04 1 MB (blind boot) + 25 s driving | same | **0 of 91692 changed** |
| HD Mega STE 2.06 4 MB + 25 s driving | same + `$AF000-$185FFF` | `$81000`, `$32A00`, `$B8200` regions: **0 changed**; `$AF000-$185FFF`: **880265 of 880640 changed** |

So:
* **`$81000-$88CFF` (32 000 B, 256-aligned) is free**: the third screen page C.
* `$B8200-$BFFFF` (32 768 B) is free on the HD build at 1 MB and 4 MB. **Not usable on floppy** (the Paper Bag
  loader's file cache starts at `$AF000`).
* `$32A00-$3682B` (15 916 B, the game's own arena slack between the 48 000-byte `$2ad00` allocation and
  `$3682c`) is free in the 3D view on the cells tested. Left unused (it is inside the game's arena).
* **`$AF000-$185FFF` is NOT free**: the game's D15R mini-OS and its buffers live at `$C0100..`. Filling that range
  at 4 MB made the machine take an illegal instruction, run its exception handler (which clears memory and resets)
  and the loader re-read HUM.FIC into `$81000` - which is what the first "everything changed" result was.
  The v1.1 fillcheck never wrote outside `$8BA00-$AEFFF`; it only *reported* the non-zero count in `$AF000-$BFFFF`.

Windows inside the payload (`$8BA00-$AEFFF`), from the build manifest plus the v1.1 `--fill` proof:

| prefix | window | size | owner |
|---|---|---:|---|
| `pal_` | `$8C014-$8C0FF` | 236 | palette |
| `tb_` | `$8C1B2-$8C3FF` | 590 | this work |
| `sav_` | `$8C72C-$8CDFF` | 1748 | HD save/load |
| `sky_` | `$8F100-$8F7FF` | 1792 | sky/panel: the hole between `snd_core` state (`$8F000`) and tables (`$8F800`); the floppy stage only loads payload code below `$90000`, so the sample-bank tail is not usable |
| `sky2_` | `$8ECEA-$8EFFF` | 790 | sky/panel state: the hole between `snd_core` code (ends `$8ECE9`) and its state (`$8F000`) |
| `key_` | `$8D816-$8D9BF` | 426 | keys |
| spare | `$8CE80-$8CFFF`, `$8D360-$8D3FF`, `$8D585-$8D5FF`, `$8D9D4-$8D9DF`, `$8DBF4-$8DBFF`, `$8ECEA-$8EFFF`, `$8F100-$8F7FF` | | unassigned |

`IMG_BASE`/`IMG_END` are unchanged (`$8BA00`/`$AF000`). `$88D00-$8B9FF` (11 520 B, directly in front of the image)
is also free but only usable if the stub's read destination and `IMG_BASE` move; not needed for v1.2.

**1 MB is enough for all of v1.2**: 32 KB for the third page, 8.6 KB of windows plus the spare gaps for the code.

## 3. Design

State block `tb_`+0 (`$8C1B2`, zeroed by the `; data:` line): `+0` VBL counter, `+2` VBL at the last flip,
`+4` mode word (0 = CPU not probed, 1 = triple buffering on, 2 = off).

* **Flip** (`tb_flip`, site `$5fd2` -> `jmp $8C1C2`): a complete copy of the flip. It rotates
  `D = $144(a5)` (drawn), `L = $148(a5)` (shown) and `S` (the third page, computed as `A+B+C-D-L`, so no table
  is needed and it recovers from any pair a mode change left behind):
  `$148 := D` (the frame just drawn is shown), `$144 := S`, base := D. A pair that is not a permutation of
  `{A,B,C}` takes the original flip (bchg/exg/store) unchanged; `D == L` (mode entry, `$5fca` sets both to
  `$7f6c`) seeds the rotation (draw into B while A is shown).
* **At most one flip per VBL**: before flipping, `tbf` waits until the VBL counter differs from the value saved at
  the previous flip. This is what makes the rotation safe: the page that was shown until the previous flip is
  restored by the pointer code during that VBL before it can become the draw page again, and every flipped frame is
  displayed at least once. (It also bounds the frame rate at 50/60 Hz on fast machines.)
* **Frame boundary** (`tb_frame`, site `$5fc2`, the whole `bsr $5fd2` + `bsr $aaa2` pair): flip, then
  `rts` when triple buffering is on (no VBL wait: the pass starts at once in the spare page) or `jmp $aaa2`
  (the original wait) when it is off. The `bra $5fa4` latch behind it is untouched.
* **VBL tick** (`tb_vbl`, site `$c600`, the fade tick `tst.w $ea(a5)/ble`): counts VBLs and then runs the two
  displaced instructions. ~40 cycles/VBL (0.025 % of the CPU), in every mode.
* **TT/Falcon**: the 68000 latches the video base at the next frame start, so a flip that no longer lands on a VBL
  boundary is harmless (the display keeps the old page until the VBL). A 68020+ (TT, Falcon) takes the base at
  once, so a mid-frame flip would tear. `tbf` therefore runs the **original** flip on a 68020+ and `tb_frame` keeps
  the original wait: on TT and Falcon the only difference from v1.1 is the VBL counter and two flag tests.
  Detection is a one-shot illegal-instruction probe (`movec cacr,d1` under a temporary `$10` vector, the handler
  drops the frame by resetting a7 from a2, exactly like `core.s cflush`), so it is CPU-based, not cookie-based.
* **Not changed**: the panel copy and dither fill still write the whole draw page (`$144`) every frame, so a third
  page can never show stale content; the text box writes through `$150(a5)`, set by the callers, as before;
  the save/load code uses the fixed `$7f6c`/`$7f74` pointers and still works.

## 4. Gates

### 4.1 Per-frame picture gate `tools/hunttb_ab.py` (foot_stand, 4 frames)

Both runs carry `test_tblock` (the elapsed-VBL latch `$5fa4` pinned to 15, so both advance the world by the same
amount per frame - without it the frames are a different number of VBLs long and the runs legitimately diverge,
the same reason `huntab --lock` exists). The patches are applied at the **3D loop top** (`pc = $253e`): applying
them at the flip itself leaves the in-flight `bsr $5fd2` return address pointing into the middle of the patched
instruction (observed: illegal instruction at `$5fc4`, then the game's reset handler). At every flip the three
pages are saved and `$144(a5)` is logged, so the picture (the 32000 bytes of the page just drawn) is compared, not a
fixed address.

```
1 base A 8fea8f6b | patched A 8fea8f6b SAME
2 base B fc336bd6 | patched C fc336bd6 SAME
3 base A 72916e20 | patched B 72916e20 SAME
4 base B a70aec63 | patched A a70aec63 SAME
```
The base run uses A,B,A,B; the patched run A,C,B,A - the same pictures, in different pages.

### 4.2 Cold boot, HD, STE 1.62 1 MB, patches = default set + tb_*

```
BOOT OK machine=ste tos=1.62 mem=1024K  in_game=True  MARKER=b'HNPO'  FLAGS=00000003
fps={'vbls': 250, 'flips': 26, 'fps': 5.2, 'vbls_per_frame': 9.615}
  peek $8c1b2: 080e080800010000          ; VBL counter $080e, last flip $0808, mode $0001 = triple buffering on
```
v1.1 stands at 5.0 fps (10 VBL/frame) on the same cell (REPORT section 3); unpatched is 4.6-4.5.

### 4.3 The seven snapshots (all IDENTICAL)

`tools/hunttb_ab.py`, 3 frames x 1 start point each (foot_stand: 4 frames), same base/only sets as 4.1:

```
foot_stand: IDENTICAL (4 frames) base A,B,A,B   patched A,C,B,A
foot_walk : IDENTICAL (3 frames) base B,A,B     patched B,C,A
car_stand : IDENTICAL (3 frames) base B,A,B     patched B,C,A
car_drive : IDENTICAL (3 frames) base A,B,A     patched A,C,B
car_turn  : IDENTICAL (3 frames) base B,A,B     patched B,C,A
hills_stand: IDENTICAL (3 frames) base A,B,A    patched A,C,B
4mb_foot_stand: IDENTICAL (3 frames) base B,A,B patched B,C,A
ALL IDENTICAL
```
Frame numbers: capture 1 is the flip at the end of the frame in which the patches were applied (its drawing predates them); frames 2
and 3 (4 for foot_stand) are frames drawn *after* a triple-buffer flip, and they use page C in the patched run - so the pass that
follows a rotated flip produces the same picture as the original pass.

### 4.4 fps, foot_walk, 8 MHz, 600 VBL, Up held

```
base flips 95  fps 7.92  vbls/frame 6.32
tb   flips 104 fps 8.67  vbls/frame 5.77      (+9.5 %)
```
Cold-boot standing (STE 1 MB): 5.2 fps, v1.1 5.0, unpatched 4.5-4.6.

### 4.5 Floppy, third page proved

`build/tb_fl3` (lean 81x10 disk, default set + tb_*), pattern at `pc = $800`, STE 1.62 1 MB:
```
BOOT OK in 77 s   in 3D view after 70 s
after 25.0 s Up+Left: in_game=True
[fl/ste/1.62/1024K] 43520 pattern bytes in $81000-$8b9ff: 0 changed, 0 runs
```
and again after the disk menus were opened and a save attempted:
```
[floppy STE save] 43520 pattern bytes in $81000-$8b9ff: 0 changed, 0 runs
```
The floppy loader's cache starts at `$AF000` and its stage-1 scratch is at `$B8400`, so the page is outside everything the loader
touches; the game's save reads its state from the arena and writes to disk, the load reads a file into `$23000` via the `$150` hook,
so neither reaches `$81000` [disasm of `$150` and the save path, notes `loading.md` section 2]. The completed floppy save/load round trip is in section 5.5 (the earlier attempt only looked unsaved: Hatari writes the image back on eject).

## 5. Open items closed (HunterTB2)

Tools (all in `tools/`): `hunttb_rate.py` (world rate and fps; reuses `hunthz.trace` but applies the live set at the 3D loop top `$253e`,
because the tb flip never executes `$5fee`), `hunttb_cold.py` (cold boots, state word, page-pointer sampling), `hunttb_save.py` (floppy save/load).
Builds: `build/tb2_hd`, `build/tb2_fl` = `hn_credit hn_hz jag_pad jag_stick p4_edge p4_ikbd p4_poly snd_core tb_flip tb_frame tb_vbl` (+ sample bank);
`build/tb2_flc` = the same without tb_* (control). All numbers below are from the tb_flip with the `tbi` a0 fix of 5.1.

### 5.1 A bug found by the cold boots, fixed: `tbi` clobbered a0
First Falcon floppy cold boot with tb_* in the build never reached the 3D view: the CPU sat in `$5f7e` (profile top: `0x5f7e 292644 cycles`, `0x5f82 13996`),
`$cc(a5)` stayed `$0f9e` over three samples a second apart while `$1a8(a5)` advanced (`1531, 1608, 16df`). `$5f7e` is the scripted-mode tick wait:
```
005f6a:  207a1ff0   movea.l  $7f5c(pc), a0
005f6e:  d0ed00cc   adda.w   $cc(a5), a0
005f78:  61000058   bsr.w    $5fd2          ; the flip, a0 is live across it
005f7c:  3010       move.w   (a0), d0
005f7e:  b06d01a8   cmp.w    $1a8(a5), d0
005f82:  6efa       bgt.b    $5f7e
```
The first call of `tbf` runs the one-shot CPU probe `tbi`, which used `a0` (`lea .trap(pc),a0`) as scratch; the original flip only touches d0/d1. When the first flip
is the one at `$5f78` (the mission page is a scripted-mode scene), `(a0)` is read from garbage. [INFERENCE] for the cause: the control disk without tb_* reached
the 3D view on the same machine and the same navigation; after saving a0 in `tbi` (`tb_flip.s`, `move.l a0,-(a7)` ... `movea.l (a7)+,a0`) the Falcon cell ran through the mission
page (`$cc(a5)` then moved: `0efe, 0f86, 0f5c`). The ST 1.04 / Mega STE HD cold boots before the fix passed because their first flip was not at `$5f78`.

### 5.2 World rate, tb on vs the v1.1 set (item 1)
`python3 tools/hunttb_rate.py world`: snapshot foot_walk, Up held (the `$d1` poke of hunthz), live set applied at `$253e`, window 1..9 s after the first loop top, counted in
VBLs (fast-forward). `base` = `p4_ikbd p4_edge p4_poly snd_core hn_hz` (jag_* left out: `jag_stick`'s site `$c64c` is hunthz's stick-poke breakpoint), `tb` = base + `tb_flip tb_frame tb_vbl`.
```
set  hz MHz | u/s     | hn_hz ticks/s | clock ticks/s | frames/s | cycles/VBL
base 50   8 |  100.98 |          50.0 |          50.0 |    6.684 | 160143
base 50  16 |  100.51 |          50.0 |          50.0 |    14.16 | 320833
base 60   8 |  100.93 |        50.021 |        50.021 |    6.624 | 133621
base 60  16 |  100.49 |        49.959 |        49.959 |   13.459 | 267317
tb   50   8 |  100.94 |          50.0 |          50.0 |    7.215 | 160293
tb   50  16 |  100.42 |          50.0 |          50.0 |    15.578 | 320656
tb   60   8 |  101.03 |        50.018 |        50.018 |    7.066 | 133724
tb   60  16 |  100.41 |        49.998 |        49.998 |   15.472 | 267245
```
World rate (units/s, hn_hz ticks/s, game clock ticks/s) is the same with tb on and off at 8 and 16 MHz, 50 and 60 Hz (within 0.1 u/s = 0.1 %; the 16 MHz rows differ from the 8 MHz
rows by 0.5 % in both sets, the known per-frame truncation of timing.md gate b); frames/s rise +7.9 % / +10.0 % (8 / 16 MHz, 50 Hz) and +6.7 % / +15 % (60 Hz).
The first run of this table (before the 5.1 fix) printed the same tb rows to the last digit except `tb 60 16` (49.998 vs 50.002 ticks/s, 15.411 vs 15.472 fps).

### 5.3 fps on the 7 scenes, 8 MHz, 50 Hz (item 2)
`python3 tools/hunttb_rate.py fps --mhz 8`, 12 s per run (window 1..11 s), hold: none for the stand scenes, Up for foot_walk/car_drive, Up+Left for car_turn.
```
scene            MHz | base fps | tb fps | gain
foot_stand         8 |    4.451 |  4.684 | +5.2 %   (VBL/frame 11.23 -> 10.67)
foot_walk          8 |    6.998 |  7.475 | +6.8 %   (VBL/frame 7.14 -> 6.69)
car_stand          8 |    5.556 |  5.882 | +5.9 %   (VBL/frame 9.00 -> 8.50)
car_drive          8 |    7.143 |  7.449 | +4.3 %   (VBL/frame 7.00 -> 6.71)
car_turn           8 |    6.442 |  6.883 | +6.8 %   (VBL/frame 7.76 -> 7.26)
hills_stand        8 |    7.07  |  7.576 | +7.2 %   (VBL/frame 7.07 -> 6.60)
4mb_foot_stand     8 |    4.723 |  4.99  | +5.7 %   (VBL/frame 10.59 -> 10.02)
```
(+4.3 .. +7.2 %: the VBL wait removed from each frame; frames are whole VBLs, so the gain is quantised.)

The picture gate of 4.3 was re-run after the fix (`hunttb_ab.py ... --flips 1 2 3 4 --points 1`, 7 snapshots): every one `IDENTICAL (4 frames x 1 points)`, `ALL IDENTICAL`;
patched pages A,C,B,A / B,C,A,B against base A,B,A,B / B,A,B,A (page C is used in every scene).

### 5.4 Cold boots with tb_* in the build (item 3)
`python3 tools/hunttb_cold.py hd|floppy --machine ...`: harness navigation to the 3D view, then the state block, the three sites and 60 samples of `$144/$148(a5)` (`$94a/$94e`).
Mode word = last word of the 6 bytes after `$8c1b2` (VBL, last flip, mode): 1 = on, 2 = off.
```
ST 1.04 1 MB HD (blind boot):  BOOT hd machine=st in_game=True MARKER=b'HNPO' FLAGS=00000006
  tb state $8c1b2: 0838083600010000  (VBL 2104, last flip 2102, mode 1)
  sites: $5fd2=4ef90008c1c2 $5fc2=4eb90008c2c0 $c600=4eb90008c2f0
  (draw $144, shown $148) samples: {('C', 'B'): 21, ('B', 'A'): 21, ('A', 'C'): 18}    fps 5.0, 10.0 VBL/frame
Mega STE 2.06 4 MB HD:        BOOT hd machine=megaste in_game=True MARKER=b'HNPO' FLAGS=00000003
  tb state $8c1b2: 05ad05a800010000  (VBL 1453, last flip 1448, mode 1)
  samples: {('B', 'A'): 23, ('A', 'C'): 18, ('C', 'B'): 19}                              fps 8.6, 5.81 VBL/frame
STE 1.62 1 MB floppy (hunttb_save.py): marker HNPO, in game True, tb state ...0001, pages {('C','B'): 21, ('B','A'): 18, ('A','C'): 21}
TT 3.06 4 MB, --mmu true --monitor vga --cpuclock 32, HD:  BOOT hd machine=tt in_game=True MARKER=b'HNPO' FLAGS=00000003
  tb state $8c1b2: 04aa000000020000  (VBL 1194, last flip 0, mode 2)      <- mode 2 = off; "last flip" stays 0 (the rotation never runs)
  sites: $5fd2=4ef90008c1c2 $5fc2=4eb90008c2c0 $c600=4eb90008c2f0          <- patched, going to the original-flip path
  samples: {('A', 'B'): 33, ('B', 'A'): 27}   pages drawn into: A, B only; VBL counter advancing (0x04aa -> 0x0c86); fps 50.0, 1.0 VBL/frame
TT 3.06 4 MB, same flags, floppy: in_game=True MARKER=b'HNPO' FLAGS=00000003, tb state 1cdd000000020000 (mode 2), samples {('A','B'): 28, ('B','A'): 32}, fps 7.6
Falcon 4.04 4 MB, --cpuclock 16, floppy: in_game=True MARKER=b'HNPO' FLAGS=0000000b, tb state 1fbe000000020000 (mode 2), samples {('A','B'): 33, ('B','A'): 27}, fps 6.6
  (the 3D view needed one extra click on the mission page: the blind navigation's last click is sometimes lost on the Falcon; see 5.1 for the earlier failure)
```
On TT and Falcon tb is off (mode 2): the pages are only A and B, i.e. the original bchg/exg flip, and `tb_frame` takes `jmp $aaa2` (the original wait). The VBL counter still runs
(`tb_vbl` in every mode). The TT/Falcon fps rows are the harness's own count on a different CPU/clock (not compared with tb off: nothing differs there).
Not run: plain ST floppy, TT/Falcon with 1-2 MB, real hardware.

### 5.5 Floppy save/load round trip with tb on (item 4)
Why earlier attempts "failed": (a) `huntsave.py floppy` copies the scratch disk image *before* closing Hatari, and Hatari writes a modified `.st` back only when the image is ejected or
Hatari exits, so it saw an unchanged image (md5 identical before/after) although the game had saved; (b) its `fsck.fat -n` returns 1 on this disk even unsaved (`Volume label 'HUNTER' stored in
root directory and label '' stored in boot sector and different`), so its FLOPPY line says FAIL. `tools/hunttb_save.py` inserts another image in drive A and then the scratch image again (this makes Hatari write it back) and compares
file contents. The menu navigation is `huntsave.Menus` (ESC -> row 3 Disk Operation -> row 2 Save / row 1 Load, name, Return; load ends on the mission page, one click into the world).
```
original disk md5 949746b37f1cbddb0d5af5507e138fb7
marker b'HNPO' in game True | tb state 0b010aff0001 (mode word = last 2 bytes: 0001 = on)
pages before the save: {('C', 'B'): 21, ('B', 'A'): 18, ('A', 'C'): 21}
saved at (40526, 10133) | tb state 18fd18f70001 | pages after the save: {('B', 'A'): 23, ('A', 'C'): 19, ('C', 'B'): 18}
disk md5 after the eject 5d324068d51c4677be2670b856dbb9f0  (changed: True); files whose content changed: ['00', '0F', '11']
player at the save (40526, 10133) | moved to (40311, 10341) | after the load (40526, 10133)
  RAM save-time vs RAM after-load $08efe+175 / $08246+32 / $0cde8+374 / $08ce8+192 / $09ab4+960 / $08266+16 / $55514+49152   all equal
after the load: in_game True | tb state 29fb29f60001 | pages: {('A', 'C'): 19, ('B', 'A'): 17, ('C', 'B'): 24} | pos (40526, 10437)
TBSAVE PASS
```
Slot 2 wrote the directory file `0F`, the slot file `11` and `00` (the loader's file; the same three the v1.1 floppy changes, floppy.md); the page rotation is unchanged by saving and loading.

### 5.6 `--lock` / the frame limiter `$1a7` (item 5)
`--lock` (`huntab.py`, `hunthz.py`) is a test-harness poke `w $9ad $0e` (`$1a7(a5)` = 15 VBL minimum frame time); it is not a game setting [disasm]:
```
00aaa2:  4a2d01a6     tst.b    $1a6(a5)
00aaa8:  1b6d01a701a6 move.b   $1a7(a5), $1a6(a5)
00c60a:  4a2d01a6     tst.b    $1a6(a5)
00c610:  532d01a6     subq.b   #$1, $1a6(a5)
```
These are the only four references to `$1a6/$1a7(a5)` in `$800..$12003` (grep of `m68dis.py` output for `$1a7`, `$9ad`, `$9ac`, `$1a6`); nothing ever writes `$1a7`, so
nothing in the code sets it. Observed: `$9ad` is `00` in every RAM dump (`ram_game/hw/main/mission/title2`, `ram_foot_stand`, `ram_foot_walk`, `ram_demo_sound`). The in-game ESC menu has
exactly five rows (screenshot): `GAME OPTIONS` (title), `Resume Game`, `Re-brief`, `Disk Operation`, `Quit Game` - no speed/frame setting; the manual (`HUNTER.TXT`) has none. A debugger change-watch
`b ($9ad).b ! ($9ad).b :trace` on the foot_stand snapshot saw **0 changes** over 4 s of walking, ESC menu, Disk Operation menu and Resume (control: the same kind of watch on `$9af`, the tick counter, hit at once).
So the limiter is permanently 0: `$aaa2` then only waits for the next VBL, which is the "at most one flip per VBL" rule `tbf` already enforces. tb_ does not need to honour `$1a7`;
it only matters for `--lock`-style test runs (use `test_tblock` for tb A/B gates, as 4.1 does). [INFERENCE] limits: a hacked game or a debugger poke can set `$1a7`; with tb on it would then be ignored
(frames at most one per VBL instead of N). Nothing player-facing does that. (The old note "the reload word is 11 in the cold-boot dump" in baseline.md/frameloop.md is not what the dumps show: `$9ad` = 0.)

### 5.7 Verdict
Ready for `default: yes` on the evidence above: world rate unchanged (5.2), +4..7 % fps on all seven scenes at 8 MHz (5.3), identical pictures (5.3), ST/Mega STE on (mode 1), TT/Falcon off with the original flip (5.4),
floppy save/load round trip works (5.5), the limiter is not a player setting (5.6). Nothing was flipped: the `; default: no` lines of `tb_flip.s`, `tb_frame.s`, `tb_vbl.s` and the prefix/README tables are the lead's to change (all three must change together: they `; requires:` each other).
Residual risk [INFERENCE]: no real hardware (the `$ff8203/$ff8201` mid-frame write behaviour on a real 68000 shifter is the 68000 behaviour the original flip already relies on), no plain-ST floppy, and the 5.1 class of bug
(a flip caller that keeps a register the original flip never touches): `tbf`/`tbi` now save d2, d3, a0, a2 and clobber only d0/d1 like the original; callers of `$5fd2` are only `$5f78` and `$5fc2` (`m68dis.py --callers 5fd2`).
