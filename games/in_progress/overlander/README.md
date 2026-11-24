# Overlander

- Slug: `overlander`
- Status: **in progress** (STE/TT/Falcon Enhanced **v1.0** built & verified across all 5 machines)
- Source: user floppies (copied 2026-11-16), not the VHD
- Original: Elite Systems (Atari ST, `"Overlander-Atari ST Final V1.9 06/07/88"`); Amiga audio from v1.0 1989-11-27
- Local copies: `originals/`, `alt/amiga/` and `manual/` (game files, Amiga disks and manual scans: git-ignored, never committed)
- Base: decrypted original `AUTO\RUN.PRO` from `originals/overlander_elite.zip` (`overlander.stx`, checksum-verified `0xa08be7cd`)
- Builds:
  - `dist/Overlander_hd_v1.0.zip` (hard-drive / GEMDOS release)
  - `dist/Overlander_floppy_v1.0.zip` (auto-booting 720 KB floppy image `Overlander_v1.0.st`)
- Test launchers: `./tools/run_ste.sh`, `./tools/run_megaste.sh`, `./tools/run_tt.sh`, `./tools/run_falcon.sh`, `./tools/run_st.sh`

## Files

| path | bytes | md5 |
|---|---:|---|
| `originals/overlander_elite.zip` | 222277 | ab0f41d8383fa99fd8ffe12f98668566 |
| `originals/overlander_elite.zip` : `overlander.stx` | 895452 | 27d2bff5d4644aaa104fd85505ab734b |
| `originals/Automation Menu Disk 007 (19xx)(LSD - Was -Not Was-)[a3].st` | 839680 | 77d7aba7713fc5a50e0ba91ebc77dd8e |
| `alt/amiga/Overlander v1.0 (1989-11-27)(Elite)[cr ACU][t +1 ACU].adf` | 901120 | f8bc37e81d95ae828ce91fc07d895717 |
| `alt/amiga/Overlander v1.0 (1989-11-27)(Elite)[cr Trilogy][t +3 Trilogy].adf` | 901120 | a2047abd8203b736e60d04ed471ddb44 |
| `alt/amiga/Overlander v1.0 (1989-11-27)(Elite)[cr Trilogy][t +3 Trilogy][a].adf` | 901120 | 19a6153ca99f7fe64b88b4b2d5b82742 |
| `manual/overlander_i.jpg` | 217386 | c7deeff441a8f5ad5a13ddfe96b07bf5 |
| `manual/overlander_i_2.jpg` | 136851 | bfe18b9c790904fa158f2da0659e5d62 |

The Automation disk also holds Karate II, Vampire, G, Battleships, Asteroids, Diablo and Ripped Off (menu 7, `AUTO\MENU7.PRG`).
