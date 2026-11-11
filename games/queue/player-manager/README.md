# Player Manager

- Slug: `player-manager`
- Status: **queued, not started**
- VHD source: `Atari3gb.vhd`, partition at offset 1840700928 (letters G-R), folder ::/P/PLAYERMA, partition at offset 1840700928 (letters G-R), folder ::/P/PLAYERME
- Local copy: `originals/PLAYERMA`, `originals/PLAYERME` (git-ignored)
- Loader: PP's HAGA conversion (RUNME.TOS + HAGA)
- Machine/RAM notes: HAGA, 1MB min. Both folders taken: PLAYERMA and PLAYERME share identical README/LOG/MANUAL/D15R*.FIC/PLMHA1 loader but differ in RUNME.TOS (4794 vs 4818 bytes) and in FILES/PMLA and FILES/PRD (game data; PLAYERME PRD is larger, dated 2012-08-31 vs 08-01). Likely two builds/language variants of the same game [INFERENCE: not determined which].
- Alternatives found on VHD (not copied): none
- Total: 20 files, 1035798 bytes

## Files

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
