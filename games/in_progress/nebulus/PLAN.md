# Nebulus (PP Gamex HD build): enhancement plan

Source: `originals/NEBULGX/` (Gamex: `START.TOS` + `GXUT270.PRG` + `NEBULUS.PCH` + `NEBEXE.FIC` + `NEBULTIT.FIC`;
1 MB min, 512 KB gameplay). HD-only from PP; a floppy release may be needed later (`alt/`).

## Boot (lead, done)
Hatari's GEMDOS `--harddrive` does not work for Gamex (START re-runs the disk's root sector to install its
own HD driver, then `Pterm0`). `tools/nebulus.py` builds a 16 MB FAT16 ACSI image with HDDRIVER's root sector
and partition loader (same user-supplied files as Hunter, `gamebench/hd/`) and autoruns `C:\START.TOS`.
Verified: HW-detect screen, then the title/options screen ("Mission #1", "Sound On"), then F1 starts play.

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
