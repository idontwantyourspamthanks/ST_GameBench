# Nebulus (PP Gamex HD build): enhancement plan

Source: `originals/NEBULGX/` (Gamex: `START.TOS` + `GXUT270.PRG` + `NEBULUS.PCH` + `NEBEXE.FIC` + `NEBULTIT.FIC`;
1 MB min, 512 KB gameplay). HD-only from PP; a floppy release may be needed later (`alt/`).

## Boot (lead, done; frozen in `tools/nebulus.py`)
Verified route to a running tower: cold boot, space every 2 s only while the loader screens are up (max 20 s),
stop at the RAM marker `$3d00f`="Higl", 2 s, `Right` 0.5 s, fire (`Right Ctrl`) 1.0 s. Six spaces during the
loader leave the title unable to start a game by fire (measured). Baseline: `work/snapshots/1mb_tower.sav`,
`work/dumps/tower_1mb.bin`. Notes: `work/notes/harness.md`. Tower fps by flip register: 22.05 at 8 MHz.

Hatari's GEMDOS `--harddrive` does not work for Gamex (START re-runs the disk's root sector to install its
own HD driver, then `Pterm0`). `tools/nebulus.py` builds a 16 MB FAT16 ACSI image with HDDRIVER's root sector
and partition loader (same user-supplied files as Hunter, `gamebench/hd/`) and autoruns `C:\START.TOS`.
Verified: HW-detect screen, then the loader pictures, then the game's title ("Mission #1", "Sound On"), then a tower.

## Status (2026-11-18)
- Boot: solved and frozen (`tools/nebulus.py`); in-tower snapshot/dump in `work/`.
- Input lag: path mapped (`$38498` last IKBD byte, handler `$384fc`); poll frequency and the end-to-end delay
  measurement in progress (NebInput2). Trainer agent found a tap shorter than ~40 ms can be missed.
- Frame rate: the flip routine `sub_03868a` runs 18.5 fps in the tower (148/400 VBL); 29.5% of cycles are a
  spin loop at `$3825e` waiting on a counter before drawing. Whether that caps the frame rate: NebBoot2.
- Trainers: timer freeze (`$3b0aa` 67->60) and enemies off (`$3792c` -> rts + clear `$3398c-$33993`) are
  live-verified by the lead; T/E toggle design in `patches/nt_*.s`, blob address pending the payload map.
  Not proven: a real climb to the exit door with enemies off; real hardware.
- Level data: format decoded (see `work/notes/level.md`), two edits proven, `work/level/tools/nebedit.py`.
- Delivery: `msrpatch`-style tool (`nepatch`) and the payload mechanism are NebBoot2's remaining work.

## Workstreams (user's asks, in order)
1. **Input lag.** Worst with the fire button (jump while left/right, shooting). Find where input is sampled
   relative to the frame, and why a press can be missed or delayed. Fix, measure (frames from key to action).
2. **Frame rate.** Small bump if cheap; not a priority. Needs the per-frame budget first.
3. **Trainers.** (a) remove enemies, (b) stop the timer.
4. **Level editor.** Ambitious: needs the tower/level data format (tiles, enemy/object list, level table).
5. Later housekeeping: floppy build, credit/version line, docs, packaging (house rules from Midwinter 2).

## Reference material
- `games/done/hunter/`: same Gamex loader; `tools/hunter.py` (`build_hd`), `work/notes/boot.md`,
  `work/notes/loading.md` (START.TOS unpack, RAM patches, patch-delivery design, `$150` file hook).
- Skills: `st-hatari-harness`, `game-delegation`, `st-game-speedup`.
- Emulator: `tools/stharness.py`; Hatari 2.6.1 at `~/Code/AtariST/hattari/build/src/hatari`.

## Constraints
- `originals/` is read-only. Game files never enter git. One Hatari per agent, own scratch dirs.
- Defaults change only after that game's own gates.
