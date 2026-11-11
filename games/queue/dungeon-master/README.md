# Dungeon Master

- Slug: `dungeon-master`
- Status: **queued, not started**
- VHD source: `Atari3gb.vhd`, partition at offset 1380526080 (letters 0-F), folder ::/D/DMHAGA (copied from the extracted tree `hdd/extracted/games/D/DMHAGA`, byte-compared)
- Local copy: `originals/DMHAGA` (git-ignored)
- Loader: PP's HAGA conversion (RUNME.TOS + HAGA), v1.2 English, PP Jan 2013
- Machine/RAM notes (PP's README): all ST(E), Mega ST(E), TT, Falcon, any TOS; 1 MB min. Game's own state save/load works (one file, `FILES/DMGAME.DAT`); HAGA savestates; exit to desktop.
- Also copied: `originals/DM_ADMA`, PP's HAGA variant with STE DMA audio (`RUNADMA.TOS` / `RUNYM.TOS`), STE/Mega STE/TT/Falcon only, 2 MB min. Useful reference for sound work.
- Alternatives found on VHD (not copied): `::/D/DMGX` (Gamex adaptation of v1.2), `::/D/DMH112` (Dlanoe's hard-disk adaptation, improved), `::/C/CSBH` (Chaos Strikes Back, a separate game)
- Total: DMHAGA 10 files, 749498 bytes; DM_ADMA 14 files, 1021825 bytes

## Files: DMHAGA

| path | bytes | md5 |
|---|---:|---|
| DMHAGA/DM240D.BMP | 77878 | 91bf45cba5b1946923165fcabaf8022b |
| DMHAGA/FDM250.HST | 67000 | dbd2e025f02a3ffdf20c178f022a1a4c |
| DMHAGA/FILES/D15RF.FIC | 66238 | c968ea4d4748982611f1104c3300c584 |
| DMHAGA/FILES/D15RH.FIC | 66063 | 36d430583c4992db8adc6606be9d460d |
| DMHAGA/FILES/DMLA | 97852 | ae981384d37e281a8438af0ceee4f134 |
| DMHAGA/FILES/DRD | 356300 | 4168df8e68e0bf7771e866310491c720 |
| DMHAGA/HAGA | 13448 | b34607ed9baecc5982a5a01ecaf5a3dd |
| DMHAGA/LOG.TXT | 931 | 107f14b67186aadade7a38b7e2d4e499 |
| DMHAGA/README.TXT | 574 | 39e2ade9bbda910f09ed877d03b185f2 |
| DMHAGA/RUNME.TOS | 3214 | b9c3257b9c8ea53e6ffe4dadbfb60028 |

## Files: DM_ADMA

| path | bytes | md5 |
|---|---:|---|
| DM_ADMA/DM240R.BMP | 77878 | 4a3cb019311732c9083e798c898e7ea3 |
| DM_ADMA/FDM273.HST | 69888 | 60c58e8726976283174bc5d983f81996 |
| DM_ADMA/FILES/D15RF.FIC | 66238 | c968ea4d4748982611f1104c3300c584 |
| DM_ADMA/FILES/D15RH.FIC | 66063 | 36d430583c4992db8adc6606be9d460d |
| DM_ADMA/FILES/DMLA | 97852 | ae981384d37e281a8438af0ceee4f134 |
| DM_ADMA/FILES/DRD | 356300 | 4168df8e68e0bf7771e866310491c720 |
| DM_ADMA/FILES/DSLA | 98193 | 67c67821ef723e55281b4c0399de89ac |
| DM_ADMA/FILES/SAM | 97307 | 97145ba82b3fe556690e47f13696368d |
| DM_ADMA/HAGA | 13448 | b34607ed9baecc5982a5a01ecaf5a3dd |
| DM_ADMA/LDM273.HST | 69888 | c0144883be5e5343559fb12458ce7d97 |
| DM_ADMA/LOG.TXT | 949 | 44c7ea32f2e40acad769118547b7a2bd |
| DM_ADMA/README.TXT | 797 | cda64b867ad77dfe62c73de1d8985cee |
| DM_ADMA/RUNADMA.TOS | 3518 | b6857a67a4b336b1da07f64cb955740b |
| DM_ADMA/RUNYM.TOS | 3506 | 82c9e6f6ffdc2e8c190d5d03d0d53a3d |
