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

## Queue (decided, not built yet)
- **Logic/draw split** (frame rate): the tower loop is paced by `$38214` >= `$38216` (2 VBL, 25 fps cap) and the
  game logic runs once per flip, so a faster pacer alone doubles game speed. A real 50 fps needs logic updated every
  second flip and drawing every flip; at 8 MHz the draw alone must also fit 160,256 cycles (needs a ~26% cut).
  Only worthwhile on 16 MHz+ machines. User: queue it, do not build yet.
- **Floppy release**: waiting for the user's real Nebulus floppy image; HD release first.
- **Next editor round (one owner, after NebF10Debug lands; do not start earlier: it edits `ed_editor.s`/`gen_ed.py`):**
  1. **FIRST: fix the 'Pale block' menu entry**: it places cell `$85`, which is the LIFT START slab, so every pale
     block is a lift start with no end (lift analysis: `work/notes/lifts.md`; `editor.md` wrongly calls `$85/$89/$8d`
     'solid'). Replace with a real 'Lift >' entry (from here / stop here / delete, then pick the other end; add the
     `$81` ledge under the slab; warn when a pillar blocks the lift): code in `work/lifts/ed_lift.s`
     (`build_lift_editor.py`; ~566 B: needs a 4th block in `gen_ed.py`, free ranges in `lifts.md` section 4) and
     `work/lifts/ovl_lifts.patch` for the PC tool.
  2. **Keyboard shortcuts** to set the tile type at the selected cell (one key per type, repeat-last key, shown in the
     legend); acceptance: the trainer hooks (T/E read the same `$38498` cell) are SUPPRESSED while the editor is
     active so an editor key can never toggle a trainer.
  3. **Campaign disk**: 'Load from campaign disk' / 'Save to campaign disk' (drive A:, B: optional), our own
     'Insert campaign disk, press fire' prompt (check the disk is present BEFORE opening; a failed open on an empty
     drive can raise TOS's reset/retry dialog that cannot be dismissed in-game), the game disk is never written; a tool to
     build blank campaign disks (.st/.msa) holding a fixed-size `NEBLEVEL.OVL`.
  4. The Options-page hint for F10 (if NebF10Debug does not finish it).
  F9 (PP's Gamex exit key): not worried; the README says to avoid it.

## Future (user's plan, not today): nebulus.kswapps.com
A community site for Nebulus levels and campaigns, and an Amiga version of the game ("yes this means we're also
doing an Amiga version").
- Users upload campaign disks as **Amiga ADF, Atari ST or MSA** images; the site extracts the levels and renders them
  so people can see them (a picture/preview per level), into a big library of levels and campaigns.
- Browse the library, add campaigns and levels to a **cart**, download a generated **disk image** (ST/MSA/ADF).
- Consequences for what we build now (keep these true):
  - The campaign file format (`NEBLEVEL.OVL`, `work/notes/editor.md` section 3) must be a **documented, versioned,
    platform-neutral** format (magic `NCMP`, version field, big-endian 68k data; no Atari-only fields such as RAM
    addresses), so the same file works on the Amiga build and a server can parse it without the game.
  - The PC tool (`work/level/tools/nebedit.py`) must be able to read/write/validate campaign files, render a level to
    an image (ASCII and PNG), and import/export levels; it is the seed of the site's extractor.
  - Level records carry everything needed to show and play them (base tower graphics set, rows, grid, time, name,
    enemy direction nibbles); nothing that depends on the Atari decode state.
  - Disk packaging: campaign file placement inside ST/MSA/ADF images (a game-independent campaign disk layout) needs
    its own spec later; the Atari build already loads `NEBLEVEL.OVL` from the game folder/disk.
  - Amiga version: a separate project (original Amiga Nebulus code/data, a port of the loader hooks, trainers, input
    fixes and the editor); not started, no source yet.

## Reference material
- `games/done/hunter/`: same Gamex loader; `tools/hunter.py` (`build_hd`), `work/notes/boot.md`,
  `work/notes/loading.md` (START.TOS unpack, RAM patches, patch-delivery design, `$150` file hook).
- Skills: `st-hatari-harness`, `game-delegation`, `st-game-speedup`.
- Emulator: `tools/stharness.py`; Hatari 2.6.1 at `~/Code/AtariST/hattari/build/src/hatari`.

## Constraints
- `originals/` is read-only. Game files never enter git. One Hatari per agent, own scratch dirs.
- Defaults change only after that game's own gates.
