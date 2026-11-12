# TT: brown HUD palette in the top panel (Hatari artefact, not fixable in the game)

**Verdict.** On a Hatari TT the top panel (lines 0-57) is drawn with the 3D-view palette. The cause is Hatari: its TT video path renders the whole frame once per VBL, with whatever palette is in the registers at that moment. It does not sample the palette per scanline, as the ST/STE path does. The game's palette programming is correct and runs in the right order on the TT. No game patch can fix it, so no `patches/tt_*.s` was written. A real TT is not expected to show it ([INFERENCE]: no TT hardware here).

Screenshots are in this directory: `tt_palette_cold.png` (TT cold boot, patched build), `tt_palette_ste_ref.png` (STE reference), `tt_palette_exp_hudpal.png` (the experiment below).

## 1. How the game sets the two palettes

| Step | Code | Evidence |
|---|---|---|
| Top (HUD) palette, written every VBL | VBL `$26298` → `jsr $27228` loads `[$6fa0]` and writes 16 words to `$ff8240` (`$27242-$27250`) | `m68dis 27228`; in game `[$6fa0] = $4aea` |
| HUD palette contents | `$4aea`: `000 031 052 073 014 036 057 421 532 754 333 555 777 500 740 770` (the blues) | dump `ram_ingame_lobos.bin` |
| Timer B armed every VBL | `$263a2`: TBCR=0, TBDR=`$38`, TBCR=8 (event count), enable/unmask, `$6f9c = [$4a26]` | `m68dis 263a2` |
| 3D palette, written at the split | Timer B handler `$263de` copies 16 words from `[$6f9c]` to `$ff8240` (`$26406-$26420`) and animates colour 10 (`$26448`: `move.w (a0,d0.w),$14(a1)`) | `m68dis 263de` |
| 3D palette contents | `$4a6a`: `000 030 430 040 025 411 540 050 333 444 740 777 036 522 650 057` | dump |

The brown frames in the panel are the 3D palette's entries 2, 5, 6, 10 and 13 (`430 411 540 740 522`) applied to the HUD bitmap.

## 2. Order and scanline, TT vs STE (measured)

Method: breakpoint with `:trace :once :file`, whose file runs `info video`, `m $ff8240 32`, `m $ff8400 32`. The harness is `Hatari(snapshot=…, machine='tt'|'ste')`. The TT snapshot was taken from a TT cold boot (2 MB, EmuTOS `etos1024k.img`, patched default build) in the 3D view.

| Event | TT (60 Hz) | STE (50 Hz) |
|---|---|---|
| VBL handler entry `$26298` | HBL line 0; `$ff8240` = 3D palette (`000 030 430 040 …`) | HBL line 0; `$ff8240` = 3D palette |
| After `$27228` | `$ff8240` = HUD palette | same |
| Timer B handler `$263de` entry | **HBL line 89**; `$ff8240` = HUD palette (`000 031 052 073 …`) | **HBL line 118**; `$ff8240` = HUD palette |
| 60/50 Hz first visible line | 34 | 63 |
| Timer B line relative to the first visible line | 89 − 34 = **55** | 118 − 63 = **55** |

Raw TT output (Timer B entry):
```
Video base   : 0x70000
VBL counter  : 15124
HBL line     : 89
Refresh rate : 60 Hz
00FF8240: 00 00 00 31 00 52 00 73 00 14 00 36 00 57 04 21
00FF8250: 05 32 07 54 03 33 05 55 07 77 05 00 07 40 07 70
```
Raw TT output (VBL entry, i.e. the palette left at the end of the previous frame):
```
HBL line     : 0
00FF8240: 00 00 00 30 04 30 00 40 00 25 04 11 05 40 00 50
00FF8250: 03 33 04 44 07 50 07 77 00 36 05 22 06 50 00 57
00FF8400: 00 00 00 60 08 60 00 80 00 4a 08 22 0a 80 00 a0   (TT bank 0 = ST palette mirror, ff8262 = 0)
```
Raw STE output (Timer B entry): `HBL line : 118`, `Refresh rate : 50 Hz`, `$ff8240` = `00 00 00 31 00 52 00 73 …`.

So on the TT the sequence VBL (HUD palette) → Timer B at line 55 (3D palette) is identical to the STE: same order, same relative line. The three candidate causes in the ticket are ruled out:
- **Doubled lines:** Hatari's TT run fires Timer B at the same relative line as the STE.
- **VBL ordering:** the HUD palette write precedes Timer B in both.
- **Palette bank:** `$ff8262` = 0 (bank 0 mirrors `$ff8240`), and `$ff8400` mirrors the ST writes.

## 3. Root cause: Hatari draws a TT frame with one palette

Hatari 2.6.1 `src/video.c` (same in `main`):
- `Video_InterruptHandler_VBL` (about line 4971) calls `Video_DrawScreen()` first, which for `MACHINE_TT` calls `Video_RenderTTScreen()`. That does `Video_UpdateTTPalette()`, which reads `$ff8400 + bank*32` once, then `Screen_GenDraw(VideoBase, …)` for the whole frame.
- The per-scanline raster path (`Video_StoreFirstLinePalette`, `HBLPalettes`, `Video_SetHBLPaletteMaskPointers`, `Video_EndHBL`) is ST/STE only. `Video_InterruptHandler_HBL` calls `Video_TT_RasterHBL()` instead, which only updates the video counter (its comment: "assumes the TT screen is using the same display mode during the whole frame").
- `Video_SetTimings`: "TT/Falcon don't use cycle precise video effects".
- Timer B itself is emulated on the TT: `MFP_TimerB_EventCount(pMFP_Main)` plus the second MFP.

The VBL handler's draw runs just before the game's VBL handler. The registers hold the **last** palette written in the previous frame, which is the Timer B (3D) palette, as the "VBL entry" dump shows. Hatari paints the full 320x200 frame with it: the 3D view looks right and the HUD wrong.

**Experiment proving it** (TT snapshot, then `w $4a26 $00 $00 $4a $ea` and `w $6f9c $00 $00 $4a $ea`, which makes the Timer B handler write the HUD palette too):
- The whole TT frame is now drawn with the HUD palette. The panel is blue, the same as the STE (`tt_palette_exp_hudpal.png`), and the 3D area is yellow (wrong).

Pixel stats (crop of the 640x400 picture, STE ref `1mb_ingame_foot` snapshot at `(96,58)`, TT at `(0,0)`, top 116 rows = game lines 0-57):

| TT frame | Top 116 rows differing | Mean abs diff | Rows 116-399 differing |
|---|---|---|---|
| cold boot, patched build | 39744/74240 (53.5 %) | 42.08 | 72/181760 (0.04 %) |
| `/tmp/tt_orig.png` (original game) | 39744/74240 (53.5 %) | 41.14 | 72/181760 |
| experiment (Timer B writes HUD palette) | 2148/74240 (2.9 %) | 2.62 | 177096/181760 (97.4 %) |

The 2.9 % remainder is a single colour pair, `(238,136,0)` vs `(102,102,102)`, i.e. the Timer B handler's animated colour 10 (`$14(a1)`, 8-step cycle) in a different phase. Nothing else differs. The unmodified TT frame differs from the STE only in the panel, and only by palette.

## 4. Would a real TT show it?

Probably not [INFERENCE]:
- On the TT, the shifter reads its palette registers live while scanning out. The ST palette `$ff8240` is a mirror of TT bank 0 (the TT hardware manual, `sarnau/AtariDocumentation` `atari_tt030_hardware_reference_manual.txt`: ST mode palette bank = low 4 bits of the shift mode register, `$ff8262`). Mid-frame palette writes therefore change the colour of subsequent lines.
- Per Hatari's source, the display-enable signal also drives Timer B on the TT's MFP.
- Not verified: whether Timer B in ST-low on real TT hardware counts 200-line or line-doubled DE pulses. A forum table (exxosforum.co.uk t=868) calls ST-low on the TT "Double Scan", but I could not confirm the DE-count behaviour. The game is out of spec only if the count doubles, and Hatari does not model that.

## 5. Fix?

**None. `default: no`, and no `patches/tt_*.s`.**
- A Hatari TT frame has exactly one palette. A game-side fix would have to make the HUD and the 3D view share one 16-colour palette, or switch to the TT's 8-bit mode (320x480x256) with chunky data. Both would change the game's rendering for a Hatari-only artefact.
- Anything done to the palette sequence (for example leaving the HUD palette in `$ff8240` at frame end) fixes the HUD and breaks the 3D view, as the experiment shows.
- Nothing was changed, so ST/STE/Mega STE output and the abtests are unaffected by construction.

Workarounds for visual checks:
- Use Hatari `--machine ste` or `megaste` for the screen. A TT run in Hatari is only meaningful for gameplay, timing and the 68030 code paths.
- The Hatari fix would be to render the TT's ST modes per scanline like `Video_EndHBL` does for ST/STE; I did not attempt it.
