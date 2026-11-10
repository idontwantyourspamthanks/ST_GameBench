# Hunter release credit (`patches/hn_credit.s`, HunterCredit)

Requirement: a small, discreet `v<VERSION> enhanced by dad_prg` line on a screen shown at start, in both the HD (PP Gamex) and the floppy (Paper Bag) build. The title screen (blue, orange icon boxes at the sides) is used for both: the "Paper Bag presents" screen exists on the floppy only.
Tags: **[obs]** observed (Hatari 2.6.1, STE TOS 1.62, 1 MB), **[disasm]** read from `tools/m68dis.py`.

## 1. The title screen and where it is drawn
- Files `6`, `8`, `9`, `A` are IFF ILBM pictures (`FORM....ILBMBMHD`, 320x200x4, ByteRun1). `FILES/6` (30000 B) is the title picture (HUNTER logo, landscape, ACTIVISION, 12 icon boxes). [obs: the first bytes of the files; the `$23000` buffer in `work/dumps/boot/ram_title2.bin` decodes to the title]
- The game loads it through the single file loader `$d53a` (HD: `jmp $150` hook at `$d542`; floppy: the cracker's loader copy at `$d30e`; both come back to `$d5fc/$d60a`). Its tail, identical in the HD dump and the Paper Bag dump [disasm of `ram_tail_1mb.bin` and `ram_tail_floppy_1mb.bin`, `$d60a`]:
  ```
  00d60a: 4cdf1fff   movem.l (a7)+,d0-d7/a0-a4
  00d60e: 2b7800881644 move.l $88.w,$1644(a5)
  00d614: 0c90464f524d cmpi.l #'FORM',(a0)
  00d61a: 6606       bne.b   $d622
  00d61c: 4eb900010ea2 jsr    $10ea2.l      <- site (6 bytes)
  00d622: 4280       clr.l   d0
  00d624: 4e75       rts
  ```
- `$10ea2` (IFF decode): `a0 = $1648(a5)` (the load address saved by `$d53a`, `a5 = $806`, so the long at `$1e4e`), CMAP -> 16 12-bit words at `$612a`, BODY unpacked through a scratch buffer (`$7ffc.l`) and re-interleaved **in place** at the load address. So after the `jsr` returns, the finished bitmap sits at `$23000` for the title (destinations of the other pictures: `$2AD00`).
- The same screen is displayed while the rest of the game loads and until SPACE (palette 000 002 003 014 025 136 300 500 620 666 444 333 640 530 420 310, screen base `$023000`) [obs: `m $ff8240`, `m $ff8200` at the title].
- It is part of the game's own start-up, after the loader (`START.TOS` / `HUNTER.TOS`) has applied our payload, so the **boot-phase site table** can hook it, in both builds, with the same 6-byte site `$d61c` (`jsr $10ea2.l` -> `jsr $8d400.l`). No deferred (`; load:`) hook is needed (those are HD only), no stage code.

## 2. The patch
- Hook at `$8d400` (payload range `hn_`: `$8D400..$8DBFF`, between p4_poly's tables and the `test_` range): runs the original `jsr $10ea2.l`, then draws only if the picture just decoded is the title: `($1e4e).l == $23000` AND the first six converted CMAP words at `$612a` are the title's (`000 006 028 04a 26c 48e`). Any other picture is left alone. Registers `d0-d7/a0-a2` saved around the drawing.
- Text: own 4x6 font in the patch (25 glyphs x 6 bytes: space . 0-9 _ a b c d e g h n p r v y), advance 5, centred (x = (321 - 5*len)/2 = 100 for 24 chars), rows 194..199. Pixels plotted with OR into planes 1 and 3 = colour index 10 (`$444` in the title palette: the dim grey of the sky/logo anti-aliasing; the logo itself is `$666`). The version in the string comes from `@VERSION@`, replaced by `huntpatch.py` with the `; version:` header (one place).
- Free area [obs, decoded `$23000` bitmap]: rows 196..199 are colour 0 across the whole width; rows 193..195 between the side boxes (x 45..274) are black except the tip of the V of ACTIVISION (x 154..155, rows <= 194, plus ACTIVISION's N at row 192). No glyph of the text has a pixel in the text rect at those V-tip columns.

## 3. Gates [obs]
All with `tools/huntcredit.py` (capture = bitmap saved by a breakpoint `pc = $d622 && ($1e4e).l = $23000` right after the decode, plus a screenshot of the settled title; shots in `work/shots/`, git-ignored).
- **Diff against the unpatched title, confined to the text rect** (HD: `.` = START.TOS/FILES unpatched game dir; floppy: the unmodified Paper Bag `.st`):
  ```
  hd:     190 pixels differ (orig -> patched), bounding box x 100..218 y 194..199, original colours under the text [0], new colours [10], all inside the text rect: True
  floppy: 190 pixels differ (orig -> patched), bounding box x 100..218 y 194..199, original colours under the text [0], new colours [10], all inside the text rect: True
  ```
  The decoded HD and floppy bitmaps are byte-identical to each other, original and patched.
- Screenshots: `work/shots/credit_hd_orig.png`, `credit_hd_patched.png`, `credit_floppy_orig.png`, `credit_floppy_patched.png` (STE, 1 MB): the line reads `v1.0 enhanced by dad_prg` under ACTIVISION and stays through the title animation.
- `huntpatch.py verify` and `verify --floppy`: ALL OK, site `$d61c` original `4eb900010ea2` matches both dumps.
- Cold boots of the full default set (see section 4).

## 4. Cold boots (full default set incl. sample bank)
HD STE 1 MB / STE 4 MB / ST 1.04 1 MB: 3D view, `HNPO`, FLAGS 3 / 3 / 6, 5.0 fps each. Floppy (82x11, real FDC) STE: 3D view after 88 s, `HNPO`, 4.8 fps. Floppy plain ST (fast FDC, stage gates tol 14): 3D view after 70 s, `HNPO`, FLAGS 6, 5.0 fps; the blind-click harness run ended on an "Are you sure" menu both with and without hn_credit (A/B on a build without it) = harness timing. Table in REPORT.md section 10.

## 5. Notes
- `unpack_payload` (huntpatch.py) returned one byte too many for an odd-length payload image (a hn_credit-only build ends at an odd address, the default set does not); it now truncates to the image size.
- The 3D view reuses the `$23000` buffer: file E (50152 bytes, load map in boot.md) is loaded to `$23000` before the 3D view; no text remains in the 3D view [obs: screenshot after the cold boot, `build/shots_cred/`].
