# Player Manager

- Slug: `player-manager`
- Status: **v1.1 in progress**
- VHD source: `Atari3gb.vhd`, partition at offset 1840700928 (letters G-R), folder ::/P/PLAYERMA, partition at offset 1840700928 (letters G-R), folder ::/P/PLAYERME
- Local copy: `originals/PLAYERMA`, `originals/PLAYERME` (git-ignored)
- Loader: PP's HAGA conversion (`RUNME.TOS` + `HAGA`)
- Machine/RAM notes: HAGA, **1 MB minimum** (verified on Hatari real ACSI `HDDRIVER` across 4 MB STE TOS 1.62, 1 MB STE TOS 1.62, 1 MB STE TOS 2.06, and 1 MB ST TOS 1.04, plus self-booting 1.44 MB floppy on 1 MB/4 MB STE TOS 1.62 and 1 MB ST TOS 1.04).

## v1.1 Features (Atari STE Amiga Visuals & Audio)
- **Kick Off 2 Amiga Tiled Pitch & 12-Bit Palette on STE (True Double-Buffered Ring Engine in 1 MB RAM):** All 4 Amiga pitches (`normal`, `wet`, `soggy`, `artificial`) converted to STE 12-bit RGB palettes + `80×96` tilemaps + 256 3bpp tiles (`AMIGAP0..3.BIN`), rendered into two 208×168 unmirrored ring buffers (`STE_RING_A`/`STE_RING_B`) via STE Hardware fine scrolling (`$ff8201/$03/$0d` + live `$ff8205/$07/$09` sync, `$ff820f`, `$ff8265`), Blitter-paused HBlank-locked Timer B splits (wrap + bottom HUD + jet-black border), and shared-bus (`$80`) STE Hardware Blitter masked 4bpp sprites + transparent vector radar (`X` resize, `D` toggle) + active player black underline ([patches/ko2_ste.s](patches/ko2_ste.s)).
- **Kick Off 2 Amiga STE DMA Audio:** 17 Amiga 8-bit signed PCM sound effects (`AMIGASND.BIN`, 6,258 Hz mono) played via STE DMA audio hardware (`$ff8900..$ff8924`) with zero Timer-A CPU overhead.
- **Dedicated STE Mode & Plain ST Auto-Fallback:** Atari STE / Mega STE runs the dedicated True Double-Buffered Amiga STE engine automatically (`BR_IS_STE = 1`); plain 1 MB 68000 ST auto-detects `BR_IS_STE = 0` and stays on Classic v1.0 ST mode untouched.
- **Real ACSI `HDDRIVER` & 1 MB / 4 MB Compatibility + Floppy Edition:**
  - Snapshots patched `$6800..$7020` handler back into `KO2_HND_BUF` so dynamic `HDDRIVER` `TRAP #1` / HAGA pointers stay valid on 4 MB+ machines.
  - Replaces `PMMATCH.BIN` with `PMCODE.BIN` + `reapply_pm_hooks`, streams `AMIGASND.BIN` directly into KO2's heap, and caps replay ring to 6 KB when resident `HDDRIVER` sits below `$0cb000` (1 MB TOS 2.06) so high RAM stays safely below `HDDRIVER.SYS` on 1 MB ST/STE (TOS 1.04, 1.62, 2.06).
  - Deselects floppy drives (`XBIOS Ongibit($06)`) after match/post-match loads so KO2's `$0202ac` motor-off poll never hangs when booting from floppy.
  - Discreet `"v1.1 enhanced by dad_prg"` credit on `scr2.men` and `scr3.men`.

## v1.0 Features
- **Full 1989–90 English Football League (92 clubs, 4 divisions):** `[20, 24, 24, 24]` with 2,600-player pool, 38/46-week Berger round-robin fixtures, 3-up/3-down promotion & relegation, scrolling League Names & Division Tables, paged Weekly Fixtures/Results, 92-team Cup (R0/R1 draws), and 92-team `DEMO92.DAT` wired to Demo/Restart Game ([patches/league92.s](patches/league92.s)).
- **Kick Off 2 Match Engine (50 FPS on 1 MB STE):** Genuine Kick Off 2 match engine overlay running natively at `$010000` with aftertouch, instant replays (`R`), live tactics switching (`1`–`4`), dynamic pitch conditions & referees, Cup Extra Time, Normal (5m) / Fast (3m) halves, non-clashing club kits, and full post-match stat commit back to Player Manager's 2,600-player pool ([patches/ko2_bridge.s](patches/ko2_bridge.s)).
- **New Game Setup Speedup (~4.2× faster):** Bit-exact 68000 optimisations + Option A early position rejection ([patches/micro_opt.s](patches/micro_opt.s), [work/notes/newgame_setup.md](work/notes/newgame_setup.md)).
- **HAGA Loader Fixes:** `pp_nofade` (removes grey fade on loads/saves), `pp_bigram_cache` (4 MB+ safe), and PP uncached KRD `Fread` `Fseek`-offset fix.

## Build, Play & Package
- **Build:** `python3 tools/pmpatch.py` (writes `build/game/`, requires `vasmm68k_mot`, `originals/PLAYERME`, `games/queue/kick-off-2/originals/KICKOFF2/FILES/KRD`, and `work/{ko2_ram.bin,setup_ram.bin,DEMO92.DAT}`).
- **Play:** `tools/play.sh` (launches `build/play-patched/` on Hatari 1 MB STE; `--original`, `--machine`, `--ram`, `--fresh`, `--fast-forward`).
- **Package (HD):** `tools/package.sh` (writes deterministic `dist/PlayerManager_v1.1_patched_hd_<date>.zip`).
- **Package (Floppy):** `python3 tools/mkfloppy.py` (writes self-booting 1.44 MB Atari FAT12 `spc=2` floppy `dist/PlayerManager_v1.1_floppy_<date>.st` + `.zip` with ~200 KB free for saves).
- **Notes & Benchmarks:** [PLAN.md](PLAN.md), [work/notes/newgame_setup.md](work/notes/newgame_setup.md), [work/notes/match_perf.md](work/notes/match_perf.md).

## v1.1 Release MD5s (`2026-11-26`)

| Item | MD5 |
|---|---|
| `dist/PlayerManager_v1.1_patched_hd_2026-11-26.zip` | `e0d03465df2bdfb3cdc993e3dc4dddf8` |
| `dist/PlayerManager_v1.1_floppy_2026-11-26.st` | `6bb747cb856198207d8341dc3464a0fa` |
| `dist/PlayerManager_v1.1_floppy_2026-11-26.zip` | `4602a88413e41370b3dcc69124a29ef7` |
| `build/game/HAGA` | `1074342dd4a917bafdc7d2a031e9b088` |
| `build/game/FILES/PMLA` | `bb4cdba1bf70e1b4c0c279ca28f89e49` |
| `build/game/FILES/KO2ENG.BIN` | `934b13a84279197ab58d46312253f078` |
| `build/game/FILES/KO2HND.BIN` | `a3505e2d266ec54f926b300b88d6be73` |
| `build/game/FILES/PMCODE.BIN` | `b151b784eec464874beb2a0db9810fcb` |
| `build/game/FILES/KO2STE.BIN` | `b377d2f963a5f0a36ab3b4641b7f2cf8` |
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
