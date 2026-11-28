# Player Manager

- Slug: `player-manager`
- Status: **v1.1 done**
- VHD source: `Atari3gb.vhd`, partition at offset 1840700928 (letters G-R), folder ::/P/PLAYERMA, partition at offset 1840700928 (letters G-R), folder ::/P/PLAYERME
- Local copy: `originals/PLAYERMA`, `originals/PLAYERME` (git-ignored)
- Loader: PP's HAGA conversion (`RUNME.TOS` + `HAGA`)
- Machine/RAM notes: HAGA, **2 MB minimum** (verified on Hatari and MiSTerFPGA across 2 MB & 4 MB Atari STE/ST with real ACSI `HDDRIVER` `.vhd` and self-booting 1.44 MB floppy).

## v1.1 Features (Atari STE Amiga Visuals, Audio & Match Polish)
- **Kick Off 2 Amiga Tiled Pitch & 12-Bit Palette on STE (Triple-Buffered 50/60 FPS Full-Screen 320×200 Ring Engine on 2 MB+ STE):** All 4 Amiga pitches (`normal`, `wet`, `soggy`, `artificial`) converted to STE 12-bit RGB palettes + `80×96` tilemaps + 256 3bpp tiles (`AMIGAP0..3.BIN`), rendered across the **full 320×200 visible screen** into three 448-line linear ring buffers (`$0d0000`/`$0e2800`/`$0f5000`) under a single Supervisor frame bracket via lockstep VBlank STE Hardware fine scrolling (`$ff8201/$03/$0d`, `$ff820f`, `$ff8265`), exact 0-pixel pitch-edge camera clamping across all four lines, $O(1)$ `(a3)` sprite slot indexing, **160 KB 640-sprite pre-trimmed/pre-masked/X-trimmed 4bpp cache** (`$136800..$15e7ff`, 3-blit `skew==0` + single-column `4w` skewed fast paths), direct Supervisor 1-plane NFSR transparent bottom HUD (`$168000..$169fff` 4 KB save pools, skipping zero planes), **30 KB pre-expanded 32-bit pitch tile pointer map** (`$15e800..$165fff`), **160 KB 5-scale pre-baked transparent vector radar** (`$10e800..$1367ff` split solid `$ffff` + masked words + `STE_DOT_XLUT`, hidden cleanly during player walk-out until arrival at the centre circle, with 0-stall `X` resize & `D` toggle), direct `Iorec(1)` keypress check, and active player black underline ([patches/ko2_ste.s](patches/ko2_ste.s)).
- **Automatic 50 Hz PAL Match Switch, Live `H` 60 Hz Key & Clean Restore:** Colour ST/STE setups (including 60 Hz NTSC boots) automatically switch into 50 Hz PAL (`$448.w = 1`, `$ffff820a |= 2`) on match entry for authentic Kick Off 2 speed, support pressing **`H`** live in-match to toggle **60 Hz Turbo / 50 Hz PAL** on the fly (with HUD status banner), and restore your original `$448.w` and `$ffff820a.w` on return to Player Manager ([patches/ko2_bridge.s](patches/ko2_bridge.s), [patches/ko2_ste.s](patches/ko2_ste.s)).
- **Kick Off 2 Amiga STE DMA Audio:** 17 Amiga 8-bit signed PCM sound effects (`AMIGASND.BIN`, 6,258 Hz mono) played via STE DMA audio hardware (`$ff8900..$ff8924`) with exact 16-bit word KO2 script parsing and zero Timer-A CPU overhead.
- **Authentic 1989–90 92-Club Home & Away Kits, Auto Clash Avoidance & Kit Picker:**
  - All 92 English Football League clubs carry authentic 1989–90 Home (`1st`) and Away (`2nd`) kits across all 6 verified Kick Off 2 styles (`Plain`, `Stripes`, `Chest Band`, `Sleeves`, `Shoulders`, `Sash`).
  - Luminance-weighted perceptual RGB contrast scoring (`2*|dR| + 3*|dG| + |dB|`, plus colour-family & patterned-shirt overlap checks) automatically switches to the 2nd kit (or highest-contrast fallback strip) whenever two teams' kits are too similar.
  - **2-Step New Game Club Kit Picker** ([patches/kit_picker.s](patches/kit_picker.s)) right after naming your club (e.g. `Anco United`) on `scr4.men`: pick both your **Home (1st)** and **Away (2nd)** kits with a live visual jersey preview (mouse clicks or keys `1`–`3` + `Space`), persisted in every save game at `-$24c8(a4)` and `-$24c6(a4)`.
  - **Kick Off 2 Pre-Match Screen (`ko6.men`)** before every match showing both clubs, live visual jerseys, genuinely randomized Referee (`0..23`), Pitch Condition (`NORMAL` / `WET` / `SOGGY` / `PLASTIC`), and Wind, with instant 1st↔2nd kit override before kick-off (Joystick `U/D` or `H` = Home 1st/2nd, `L/R` or `A` = Away 1st/2nd; keys `1`–`3` / `4`–`6` for custom tweaks; `Fire` / `Space` to kick off).
- **Dedicated STE Mode & Plain ST Auto-Fallback:** Atari STE / Mega STE (2 MB+) runs the dedicated Triple-Buffered 50 FPS Amiga STE engine automatically (`BR_IS_STE = 1`, `STE_BIG_RAM = 1`); plain 2 MB+ 68000 ST auto-detects `BR_IS_STE = 0` and stays on Classic v1.0 ST mode untouched.
- **Real ACSI `HDDRIVER`, MiSTerFPGA & 2 MB / 4 MB+ Compatibility + Floppy Edition:**
  - 32-bit-clean `HAGA` `phystop >> 19` RAM clamp (`HAGA+$014c` & `HAGA+$21a0`) for cold-boot stability on MiSTerFPGA and 2 MB / 4 MB+ machines, plus dynamic `HDDRIVER` `TRAP #1` / HAGA pointer preservation across `KO2_HND_BUF`.
  - Replaces `PMMATCH.BIN` with `PMCODE.BIN` + `reapply_pm_hooks`, streams `AMIGASND.BIN` directly into KO2's heap, and renders a native-styled centred `"LOADING..."` indicator on *The Line Up* screen.
  - Deselects floppy drives (`XBIOS Ongibit($06)`) after match/post-match loads so KO2's `$0202ac` motor-off poll never hangs when booting from floppy.
  - Discreet `"V1.1 ENHANCED BY DAD_PRG"` credit on `scr2.men` and `scr3.men` (hooked cleanly at `$010540` / `$01054c` so `$010554` click-retry branches stay intact).

## v1.0 Features
- **Full 1989–90 English Football League (92 clubs, 4 divisions):** `[20, 24, 24, 24]` with 2,600-player pool, 38/46-week Berger round-robin fixtures, 3-up/3-down promotion & relegation, scrolling League Names & Division Tables, paged Weekly Fixtures/Results, 92-team Cup (R0/R1 draws), and 92-team `DEMO92.DAT` wired to Demo/Restart Game ([patches/league92.s](patches/league92.s)).
- **Kick Off 2 Match Engine (50 FPS):** Genuine Kick Off 2 match engine overlay running natively at `$010000` with aftertouch, instant replays (`R`), live tactics switching (`1`–`4`), dynamic pitch conditions & referees, Cup Extra Time, Normal (5m) / Fast (3m) halves, non-clashing club kits, and full post-match stat commit back to Player Manager's 2,600-player pool ([patches/ko2_bridge.s](patches/ko2_bridge.s)).
- **New Game Setup Speedup (~4.2× faster):** Bit-exact 68000 optimisations + Option A early position rejection ([patches/micro_opt.s](patches/micro_opt.s), [work/notes/newgame_setup.md](work/notes/newgame_setup.md)).
- **HAGA Loader Fixes:** `pp_nofade` (removes grey fade on loads/saves), `pp_bigram_cache` (4 MB+ safe), and PP uncached KRD `Fread` `Fseek`-offset fix.

## Build, Play & Package
- **Build:** `python3 tools/pmpatch.py` (writes `build/game/`, requires `vasmm68k_mot`, `originals/PLAYERME`, `games/queue/kick-off-2/originals/KICKOFF2/FILES/KRD`, and `work/{ko2_ram.bin,setup_ram.bin,DEMO92.DAT}`).
- **Play:** `tools/play.sh` (launches `build/play-patched/` on Hatari 2 MB STE; `--original`, `--machine`, `--ram`, `--fresh`, `--fast-forward`).
- **Package (HD & Standalone VHD):** `tools/package.sh` (writes deterministic `dist/PlayerManager_v1.1_patched_hd_<date>.zip` and standalone auto-booting `dist/PlayerManager_v1.1_patched_vhd_<date>.zip`).
- **Package (Floppy):** `python3 tools/mkfloppy.py` (writes self-booting 1.44 MB Atari FAT12 `spc=2` floppy `dist/PlayerManager_v1.1_floppy_<date>.st` + `.zip` with ~200 KB free for saves).
- **Notes & Benchmarks:** [PLAN.md](PLAN.md), [work/notes/newgame_setup.md](work/notes/newgame_setup.md), [work/notes/match_perf.md](work/notes/match_perf.md).

## v1.1 Release MD5s (`2026-11-27`)

| Item | MD5 |
|---|---|
| `dist/PlayerManager_v1.1_patched_hd_2026-11-27.zip` | `6485bd4e7517c979c590aab7aaf92a21` |
| `dist/PlayerManager_v1.1_patched_vhd_2026-11-27.zip` | `205223d28976225f1782b27e441f304b` |
| `dist/PlayerManager_v1.1_floppy_2026-11-27.st` | `951c51aa52e70cc7abf0b94e54e82ffc` |
| `dist/PlayerManager_v1.1_floppy_2026-11-27.zip` | `6418bfdfe70f2191ed5076fc513ffd88` |
| `build/game/HAGA` | `5d573a9cd79de06588ce53da9aa44e05` |
| `build/game/FILES/PMLA` | `ad23b74e7c9a923db56503917dd1bd14` |
| `build/game/FILES/KO2ENG.BIN` | `934b13a84279197ab58d46312253f078` |
| `build/game/FILES/KO2HND.BIN` | `a3505e2d266ec54f926b300b88d6be73` |
| `build/game/FILES/PMCODE.BIN` | `b151b784eec464874beb2a0db9810fcb` |
| `build/game/FILES/KO2STE.BIN` | `5a974b7487423d32e51bf28ab0351ec8` |
| `build/game/FILES/AMIGASND.BIN` | `d5bd5ab3b9e1051ed23d2d778a718753` |
| `build/game/FILES/AMIGAP0.BIN` | `29cb99c7587974a2b2fb4a571c31eaa7` |

## v1.0 Release MD5s (`2026-11-26`)

| Item | MD5 |
|---|---|
| `dist/PlayerManager_v1.0_patched_hd_2026-11-26.zip` | `0dec01df2c2a018eec3fcc34c658eb8b` |
| `build/game/HAGA` | `1074342dd4a917bafdc7d2a031e9b088` |
| `build/game/FILES/PMLA` | `65c6932437515bc09c8f85b355d3ec93` |
| `build/game/FILES/KO2ENG.BIN` | `934b13a84279197ab58d46312253f078` |
| `build/game/FILES/KO2HND.BIN` | `a3505e2d266ec54f926b300b88d6be73` |
| `build/game/FILES/PMMATCH.BIN` | `573090dad53da0a8539136558de7a1ae` |

## Original Intake Files

| path | bytes | md5 |
|---|---:|---|
| PLAYERMA/FILES/D15RF.FIC | 66238 | c968ea4d4748982611f1104c3300c584 |
| PLAYERMA/FILES/D15RH.FIC | 66063 | 36d430583c4992db8adc6606be9d460d |
| PLAYERMA/FILES/PMLA | 80723 | 64edf2d956bc67bbfc37a9363e1b5953 |
| PLAYERMA/FILES/PRD | 159554 | c70f5cff9297698023b7ce370f4e0b03 |
| PLAYERMA/HAGA | 13448 | b34607ed9baecc5982a5a01ecaf5a3dd |
| PLAYERMA/LOG.TXT | 780 | 9b60f02578ffa3d6a46359bc9ec15ad0 |
| PLAYERMA/MANUAL.TXT | 23584 | 836b6dd45dff2a409cb3fe7fa846c77f |
| PLAYERMA/PLAYMA.PCH | 102470 | b5fc4c97fa3ee2f5d3bca9d41a4579a3 |
| PLAYERMA/README.TXT | 648 | 10b7acdc90d84096a4fcec26b3a7862e |
| PLAYERMA/RUNME.TOS | 4794 | ff1a60df5be0e78c4283101802af88ba |
| PLAYERME/FILES/D15RF.FIC | 66238 | c968ea4d4748982611f1104c3300c584 |
| PLAYERME/FILES/D15RH.FIC | 66063 | 36d430583c4992db8adc6606be9d460d |
| PLAYERME/FILES/PMLA | 79409 | 157f0423fab4e8bec2dbbb00457a69c5 |
| PLAYERME/FILES/PRD | 160038 | 6c9c2dd0251bd6370bf7f4a84d53211d |
| PLAYERME/HAGA | 13448 | b34607ed9baecc5982a5a01ecaf5a3dd |
| PLAYERME/LOG.TXT | 780 | 9b60f02578ffa3d6a46359bc9ec15ad0 |
| PLAYERME/MANUAL.TXT | 23584 | 836b6dd45dff2a409cb3fe7fa846c77f |
| PLAYERME/PLAYMA.PCH | 102470 | b5fc4c97fa3ee2f5d3bca9d41a4579a3 |
| PLAYERME/README.TXT | 648 | 10b7acdc90d84096a4fcec26b3a7862e |
| PLAYERME/RUNME.TOS | 4818 | a320e198918aa0340a4d8322f23004ac |
