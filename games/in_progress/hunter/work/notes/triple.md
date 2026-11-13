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
so neither reaches `$81000` [disasm of `$150` and the save path, notes `loading.md` section 2]. A *completed* save/load round trip
on the floppy was not driven to the end (the menu clicks went back to the 3D view); the disk image md5 was unchanged, so no save
was actually written in that attempt.

## 5. Not done (state at the end of this session)

* fps measured on foot_walk (7.92 -> 8.67 fps) and the cold-boot standing cell (5.0 -> 5.2); the other five scenes
  were not timed.
* **World rate not measured**: `world_rate($ab2)` returned 0.0 units/s in both runs on foot_walk (the probe did not
  see the player move), so that check is void. The design does not touch `$1aa`/`$1ac`/`$1a7`, the latch or hn_hz's
  world gate, so the world speed should be unchanged [INFERENCE] - it needs a working measurement.
* Cold boots with tb_* on ST, Mega STE, TT (`--mmu true`) and Falcon floppy: only the HD STE 1 MB cold boot and the
  floppy STE 1 MB cell were run.
* The floppy save/load round trip (see 4.5) and the plain-ST floppy cell (the blind harness missed the menus).
* `huntpatch.py build`/`build --floppy` with *every* v1.2 prefix at once (key_+sav_+pal_+sky_+sky2_+tb_+p4_+snd_+jag_+hn_):
  the build with the default set + tb_* is OK for both.
* `huntpatch.py build`/`build --floppy` with every v1.2 prefix at once (the individual build with
  p4_*/snd_core/hn_*/jag_* + tb_* is OK: "built ... 11 patch(es)", payload `$8ba00..$ae4dd`).
