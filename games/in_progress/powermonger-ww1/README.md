# Powermonger: World War One Edition (1992, Bullfrog / Electronic Arts): enhanced floppy

Status: **in progress, stage 2 of `PLAN.md` done** (delivery core + floppy writer; credit line, no copy protection (`pm_noprot`, `pm_noprot_box`, `pm_nokeydisk`), fixed 4.00/s world tick (`tick_*`), keyboard shortcuts (`qol_keys`, `qol_keys2`)).
Base (user decision 2026-11-23): the **EA original** floppy. The cracked versions are for comparison only.
Plan and decisions: [`PLAN.md`](PLAN.md). Results of the stages: [`work/notes/RESULTS_stage01.md`](work/notes/RESULTS_stage01.md), [`work/notes/RESULTS_stage02.md`](work/notes/RESULTS_stage02.md). Method and reference project: `games/done/powermonger/`.

- Build: `python3 tools/wwpatch.py verify | list | build [--floppy] [--only NAME ...] [--none] [--corrupt] [--fill] [--out DIR]` (needs `disks/ea.st`, `vasmm68k_mot`).
  `build --floppy` writes `build/default/floppy.st` = the EA disk with a new `AUTO\WW1.PRG` (the payload rides in the program's data segment); nothing else on the disk changes.
- Gates: `python3 tools/wwgate.py cell|handover ...` (docs in the file), `tools/wwtick.py snap|rate|ab` (tick rates, per-tick state equality), `tools/wwkeys.py` (key == click, phantom click), `tools/wwgrid.py points|handlers`; the chains: `tools/stage01_gates.sh`, `tools/stage02_gates.sh`. Logs in `work/runs/`.
- Intake: `python3 tools/stx2st.py <EA .stx> disks/ea.st`; unpacker of the game program: `tools/wwdepack.py`; address port from master's Powermonger: `tools/addrmap.py`.
- Notes (one topic each): `work/notes/intake.md` (disk, files, the Powermonger-disk requester), `delivery.md` (how the patch gets in), `placement.md` (why `$72000..$77FFF`), `addrmap.md` (master -> WW1 addresses).

**The unpatched game asks for the original Powermonger floppy** on the first START NEW CONQUEST of a session (then for the WW1 disk back). That request is a key-disk check (it only loads the file `DATA\\SPRITE8.DAT` from drive A: and throws it away): the enhanced disk removes it (`patches/pm_nokeydisk.s`, evidence in `work/notes/RESULTS_stage02.md`). Tested so far with the WW1 disk only: new conquest, save/load, lose, win, a third land, 5 minutes of play. **Not yet tested: the end of a whole campaign.** The game's resource table names `END_PIC1`, `END`, `BITMAP` and `CAP_SPR`, which are not on the WW1 disk; whether the campaign end needs them is open (gate planned before release).

Game files are git-ignored. Put your own copies here:

- `originals/`: the zip of the EA release (`powermonger_-_world_war_i_edition_electronic_arts.zip`; the cracked releases are also there, comparison only);
- `disks/ea.st`: the converted floppy image (below);
- `extracted/ea/`: files extracted from it, e.g. `MTOOLS_SKIP_CHECK=1 mcopy -s -m -n -i disks/ea.st :: extracted/ea/`.

## Intake md5s

| Item | MD5 | Bytes |
|---|---|---|
| `originals/powermonger_-_world_war_i_edition_electronic_arts.zip` | `934d176f1781b22bb03b276aa067c130` | 889898 |
| the `.stx` inside (Pasti) | `8d2f6c6b6ecc060524950aab4ffefb7b` | 889658 |
| `disks/ea.st` (`tools/stx2st.py`; 1 side, 80 x 10 sectors, FAT12) | `95354c89884a4cb82b62fe63400bf750` | 409600 |
| `AUTO\WW1.PRG` (text 76304 B, one RNC-variant packed program) | `dc93b917458125398a072c95f452f4b0` | 76336 |
| resident game image, derived from `WW1.PRG` by `tools/wwdepack.py` (`$576..$1d2ad`), identical to the RAM at the hand-over | `694b94a1e1e06aa05bd6579cbb8c3778` | 118072 |
| data: `CAPGRAPH.PAK` `FX.PAK` `LOSE.PAK` `MAP.PAK` `QAZ.PAK` `SPRITE8/16/24/32.PAK` `TEXTURES.PAK` `WIN.PAK` `MAPDATA.DAT` | see `work/notes/intake.md` | 291148 together |

Free space on the disk: 36864 B (the patched `WW1.PRG` grows by about 0.6-1 KB for the credit line).

## Running

Hatari 2.6.1 (`~/Code/AtariST/hattari/build/src/hatari`), STE, TOS 1.62, 1 MB: `--disk-a build/default/floppy.st`. Boot, type a name, START NEW CONQUEST, swap in the original Powermonger disk when asked, swap the WW1 disk back, pick the small island at the top of the chart.
Stage-1 results on STE TOS 1.62 and Mega STE TOS 2.06 are in `work/notes/RESULTS_stage01.md`.

## Release md5s

(none yet: no release; the stage-1 build md5s are in `work/notes/RESULTS_stage01.md`.)
