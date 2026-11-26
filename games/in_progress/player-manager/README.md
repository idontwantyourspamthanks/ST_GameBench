# Player Manager

- Slug: `player-manager`
- Status: **v1.1 complete**
- VHD source: `Atari3gb.vhd`, partition at offset 1840700928 (letters G-R), folder ::/P/PLAYERMA, partition at offset 1840700928 (letters G-R), folder ::/P/PLAYERME
- Local copy: `originals/PLAYERMA`, `originals/PLAYERME` (git-ignored)
- Loader: PP's HAGA conversion (`RUNME.TOS` + `HAGA`)
- Machine/RAM notes: HAGA, **1 MB minimum** (verified on Hatari 1 MB 8 MHz STE TOS 1.62 & 1 MB 8 MHz ST TOS 1.04, 50 Hz PAL).

## v1.1 Features (Atari STE Amiga Visuals & Audio)
- **Kick Off 2 Amiga Tiled Pitch & 12-Bit Palette on STE (49.75–50.00 FPS in 1 MB RAM):** All 4 Amiga pitches (`normal`, `wet`, `soggy`, `artificial`) converted to STE 12-bit RGB palettes + `80×96` tilemaps + 256 3bpp tiles (`AMIGAP0..3.BIN`), rendered via STE Hardware Corkscrew fine scrolling (`$ff8201/$03/$0d`, `$ff820f`, `$ff8265`) and STE Hardware Blitter masked 4bpp sprites + Compact Mini-Radar, Player Name, Score, Match Clock, and Event Banners ([patches/ko2_ste.s](patches/ko2_ste.s)).
- **Kick Off 2 Amiga STE DMA Audio:** 17 Amiga 8-bit signed PCM sound effects (`AMIGASND.BIN`, 6,258 Hz mono) played via STE DMA audio hardware (`$ff8900..$ff8924`) with zero Timer-A CPU overhead.
- **Live View Toggle (`V` key) & Plain ST Auto-Fallback:** Press `V` in-match on STE to toggle live between Amiga STE and Classic ST views; plain 1 MB 68000 ST auto-detects `BR_IS_STE = 0` and runs Classic ST mode cleanly.

## v1.0 Features
- **Full 1989–90 English Football League (92 clubs, 4 divisions):** `[20, 24, 24, 24]` with 2,600-player pool, 38/46-week Berger round-robin fixtures, 3-up/3-down promotion & relegation, scrolling League Names & Division Tables, paged Weekly Fixtures/Results, 92-team Cup (R0/R1 draws), and 92-team `DEMO92.DAT` wired to Demo/Restart Game ([patches/league92.s](patches/league92.s)).
- **Kick Off 2 Match Engine (50 FPS on 1 MB STE):** Genuine Kick Off 2 match engine overlay running natively at `$010000` with aftertouch, instant replays (`R`), live tactics switching (`1`–`4`), dynamic pitch conditions & referees, Cup Extra Time, Normal (5m) / Fast (3m) halves, non-clashing club kits, and full post-match stat commit back to Player Manager's 2,600-player pool ([patches/ko2_bridge.s](patches/ko2_bridge.s)).
- **New Game Setup Speedup (~4.2× faster):** Bit-exact 68000 optimisations + Option A early position rejection ([patches/micro_opt.s](patches/micro_opt.s), [work/notes/newgame_setup.md](work/notes/newgame_setup.md)).
- **HAGA Loader Fixes:** `pp_nofade` (removes grey fade on loads/saves), `pp_bigram_cache` (4 MB+ safe), and PP uncached KRD `Fread` `Fseek`-offset fix.

## Build, Play & Package
- **Build:** `python3 tools/pmpatch.py` (writes `build/game/`, requires `vasmm68k_mot`, `originals/PLAYERME`, `games/queue/kick-off-2/originals/KICKOFF2/FILES/KRD`, and `work/{ko2_ram.bin,setup_ram.bin,DEMO92.DAT}`).
- **Play:** `tools/play.sh` (launches `build/play-patched/` on Hatari 1 MB STE; `--original`, `--machine`, `--ram`, `--fresh`, `--fast-forward`).
- **Package:** `tools/package.sh` (writes deterministic `dist/PlayerManager_v1.0_patched_hd_<date>.zip`).
- **Notes & Benchmarks:** [PLAN.md](PLAN.md), [work/notes/newgame_setup.md](work/notes/newgame_setup.md), [work/notes/match_perf.md](work/notes/match_perf.md).

## v1.1 Release MD5s (`2026-11-26`)

| Item | MD5 |
|---|---|
| `dist/PlayerManager_v1.1_patched_hd_2026-11-26.zip` | `e7d041a28a7fa01bb5190f828699fff3` |
| `build/game/HAGA` | `1074342dd4a917bafdc7d2a031e9b088` |
| `build/game/FILES/PMLA` | `11a0c52b134f00d796b1a75fc13911ba` |
| `build/game/FILES/KO2ENG.BIN` | `934b13a84279197ab58d46312253f078` |
| `build/game/FILES/KO2HND.BIN` | `a3505e2d266ec54f926b300b88d6be73` |
| `build/game/FILES/PMMATCH.BIN` | `573090dad53da0a8539136558de7a1ae` |
| `build/game/FILES/KO2STE.BIN` | `9f2abf418e91fd533cb509a2fe1fe2f1` |
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
