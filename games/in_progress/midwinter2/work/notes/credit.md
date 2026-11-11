# Release credit on the logo screen (`patches/mw2_credit.s`, VERSION 1.2)

Placement chosen by the user: bottom of the orange MIDWINTER II logo screen (the one followed by "Insert Graphics Disk" on floppy),
text `v1.2 enhanced by dad_prg`, a colour already in that screen's palette, empty pixels only, palette and logo art untouched.
Tools used (all in `work/credit/`, git-ignored): `tl.py` (timeline screenshots), `bp3.py`/`bp4.py`/`gate.py` (breakpoint dumps),
`bootdump.py`, `pdiff.py`. Raw dumps in `work/credit/*.scr` (screen RAM `$50000-$7FFFF`).

## 1. The screen exists in both builds (unpatched timelines, STE TOS 1.62, 1 MB, `work/credit/tl/*_orig_*.png`)
- Floppy: GRAFIX title pictures from the boot stub, black, **MIDWINTER logo (grows, then the "II" appears) -> "Insert Graphics Disk / press any key"**.
- HD: PP's menu, intro picture, FLAMES OF FREEDOM, black, **the same MIDWINTER II logo** (no prompt text on screen), then the island intro.
- The FLAMES OF FREEDOM picture belongs to the boot stub (`$4D9A6`: files 2-5 -> `$50000-$68000`, shown by the stub's VBL code
  `$4df30`); at game entry `$3104` (`jmp $312a8`) the displayed screen is that picture (video base `$50000`/`$58000`, palette `$540,$401,..`).
  The logo is drawn by the GAME after that, i.e. when our payload is resident on both media.

## 2. Where it is drawn (disassembly of FFA file 8/9 as loaded, `/tmp/cr/boot.bin` = $806 file 8 + $3104 file 9)
Breakpoint stacks (`bp4.py`, floppy and HD identical): `$312da` -> `$1f4fc` (return `$2c570`) -> `$28a60` (check "graphics disk", return `$28d2c`/`$1f51e`) -> `$28b20`.
`sub_01f4fc` (FFB-f1 overlay range `$18d96-$210b2`, but that overlay is only loaded much later):
```
01f5dc:  206e0004   movea.l $4(a6),a0        ; B = $70000 (displayed)
01f5e0:  2256       movea.l (a6),a1          ; A = $60000 (draw)
01f5e2:  4eb84f30   jsr     $4f30.w          ; copy B -> A   (sub_2a474, 32000 bytes)
01f5e6:  4eb84eee   jsr     $4eee.w
01f5ea:  3d7c0001011e move.w #$1,$11e(a6)    ; font 1   (PP patch: jsr $314, which nops the stub's sector read and does the same)
01f5f0:  3d7c00a0000e move.w #$a0,$e(a6)     ; <-- SITE (6 bytes)
01f5f6:  3d7c00a00010 move.w #$a0,$10(a6)
01f5fc:  43f900013100 lea.l   $13100.l,a1    ; "\x01\x0f\x05Insert Graphics Disk"
01f602:  4eb84ed0     jsr     $4ed0.w        ; text routine -> $2abd2
...  $1f606.. second line "press any key" at y=$aa
01f61c:  4eb84f36     jsr     $4f36.w        ; flip: A displayed
01f620:  jsr $26fd0 / $4f66 ... key wait   (PP: `$1f636` beq -> nop, so on HD there is no wait)
01f63c:  4eb84f36     jsr     $4f36.w        ; flip: B displayed (the bare logo)
01f644:  jsr $2b1f6 ... file $6f/$6e loads (the intro)
```
Registers at the site: `a6 = $770e`, (a6) = `$60000`, 4(a6) = `$70000`, 8(a6) = `$68000` (m $770e, floppy and HD, `bp3.py`).
So on floppy the prompt screen is A until a key is pressed and then B; on HD (no wait) A is shown for ~0 frames and **B, the bare logo,
stays up while the intro files load**. The credit therefore has to be in BOTH buffers.

Palette at the site (both builds): `$000 $500 $630 $740 $750 $762, 6..14 = $000, 15 = $777`. Free rows: the prompt's last glyph row is 178;
rows 179-199 are colour 0 in both buffers (printed from the dump). Text: font 1 glyph box = Y..Y+8 (caps 7 rows, descenders +8).

## 3. The patch
`jsr $b9000.l` over the displaced `move.w #$a0,$e(a6)`; the blob saves `$0e..$49(a6)` and `$11e..$126(a6)`, draws the string with `jsr $4ed0.w`
(codes `01 <colour>` and `05` = centre; x=160, Y=188, colour 2 = `$630`), copies rows 188..197 of the draw buffer to the other buffer, restores the
saved words and registers, replays the displaced move. VERSION: one `; version:` header, `@VERSION@` in the string, PATCHES.TXT, FLOPPY.TXT, zip names.
`$1f5f0` is a boot-phase site that lies inside the overlay range, so `verify` uses `work/dumps/ram_boot_hd1mb.bin` for the dump cross-check
(`check_site`): `declared orig 3d7c00a0000e / image match / ramdump match`. `ram_boot_fl1mb.bin` (unpatched floppy boot at `$312a8`) has the same
bytes at `$1f5f0` (`3d7c00a0000e3d7c00a00010`); the two dumps differ in `$3104-$3dc00` only at PP's patch addresses (`$1f5ea`, `$1f636`, `$27ac4`, ...).

## 4. Gates (STE TOS 1.62, 1 MB unless noted)
See REPORT.md and the task result for the raw outputs. Pixel diff vs the unpatched screens at the same code point (`pdiff.py`):
```
floppy @1f620 $60000 bytes differ 111 pixels 343 bbox x 93 225 y 188 196 old colours [0] new colours [2]
floppy @1f620 $70000 bytes differ 111 pixels 343 bbox x 93 225 y 188 196 old colours [0] new colours [2]
HD     @1f644 $60000 bytes differ 111 pixels 343 bbox x 93 225 y 188 196 old colours [0] new colours [2]
HD     @1f644 $70000 bytes differ 111 pixels 343 bbox x 93 225 y 188 196 old colours [0] new colours [2]
```
Palette registers identical before/after.
