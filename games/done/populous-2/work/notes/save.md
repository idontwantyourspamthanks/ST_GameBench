# Populous 2: in-game SAVE GAME / LOAD GAME (`pop2_save`, `pop2_save_w`, `pop2_save_d`)

2026-11-13, Pop2Save3 (continues Pop2Save2). **Status: all gates closed (Pop2SaveClose, 2026-11-13: full disk on ACSI, HD write-protect, lv2, p2tick ab / p2abtest / p2noquest regressions; raw outputs in `work/gates/save_*.txt`); the three patches are `; default: yes` and packaged.** Evidence tags: [obs] = raw output of a cell in `work/scratch/save/` (`sv.py` library,
`cell_main.py`, `cell_level.py`, `cell_err.py`, `cell_floppy.py`), [disasm] = `tools/m68dis.py`, [INFERENCE] = unproven. Design and contract of the game's disk layer: see the header
notes of `patches/pop2_save.s` (the three call sites `$2cb0e` dir / `$2cbe4` write / `$2cc58` read go to a GEMDOS blob run inside HAGA's own TOS swap).

## 1. What changed in this round (all in `patches/pop2_save.s`)
* **Durability**: after every write `Dfree` (drive of the path, else current) = reads the whole FAT, which makes GEMDOS write back its dirty directory / FAT buffers (idea and
  mechanism from HunterSave's `sav_sync`; note its Dfree call pushes no drive word, mine does). Kill test (SIGKILL of Hatari N s after the save returned, then `fsck.fat -n` + `mtype`
  of the image, ACSI + HDDRIVER): **without Dfree (`build/Pop2SaveNoFlush`) STE: 1 s, 5 s, 20 s all LOST** (`fsck: FATs differ ... /FILES/PERS.GAM Contains a free cluster (854)`, file unreadable);
  **with it, 2 runs each at 1 / 5 / 20 s: clean + file == RAM at the write, on STE, Mega STE (TOS 2.06) and TT (TOS 3.06): 18 of 18.** A cold boot on the post-kill image loaded the save (RAM after read == RAM at the save).
* **TT directory** was empty: cause = **Hatari's GEMDOS emulation**, not the PMMU view of the DTA. `gemdos.c` finds the DTA as `ReadLong(ReadLong(act_pd) + $20)` with `act_pd` = p_run, read from PHYSICAL memory, where on a TT
  (HAGA swaps by PMMU remap) the game's RAM sits, not TOS's. [obs] with the original blob the TT list is empty (`ttn_dir.png`); the DTA written by Hatari has the right size/date (dump `tt_dta.bin`). Fix: during the dir call the
  game-side copy of p_run (virtual `$200000 + p_run`) points at a fake basepage whose `+$20` = our DTA, restored afterwards; a real TOS never reads it. [obs] list shows T1/T2 (`r3_hd_tt_dir.png`). On ACSI the real TOS lists correctly (`r3_acsi_tt_dir.png`).
* **Missing-file box**: OK dismisses it and returns to the requester; the button's hit row is **y = 184** in screenshot coordinates (the glyph centre y = 177 misses). Fixed in all cells; the cell then cancels and the game runs (`after missing-file error: game running=True ... in_play=True` in every run below).
* **Floppy save-disk flow** (Main's request): the boot disk is full, so on the floppy (default drive A:/B:, no drawer typed) the saves go to the ROOT of a separate formatted disk (`Populous2_save.st`, blank 720K made by `pop2patch.py build --floppy`, 730,112 B free = 12 saves).
  If the disk in the drive is the game disk (root has HAGA), has no room for a save, or cannot be read, the game's own message box (`$14b2e`, the call its DISK FILE ERROR path uses) shows **INSERT SAVE DISK**; OK repeats the call (one more silent try:
  the first access after a swap can fail). TOS's disk-change detection does not run while the game owns the interrupts (GEMDOS kept answering from cached FAT/dir sectors after a swap, and would write the new disk with the old FAT), so every floppy-mode call first invalidates the BIOS cache buffers of A:/B: (`_bufl` `$4b2` lists, `b_bufdrv = -1`).
  The game disk is **not needed again** (P2D is in RAM; a level change with the save disk in A: worked, 4 `$140` calls). [obs] on STE TOS 1.62 (`/tmp` cells driven interactively; screenshots `f4_*`, `f5_*`, `f6_*`, `fl_*` in `work/scratch/save`):
  SAVE requester with the boot disk -> INSERT SAVE DISK (`f5_1_boot_box.png`); swap, OK, SAVE F1: `F1.GAM` 56,690 B on the ejected disk == RAM at the write, `fsck.fat` clean; LOAD from it == RAM at the save; directory lists it after a swap (`f4_load_list.png`);
  empty valid disk: no box (`f5_2_emptydisk.png`); 12 saves fit (41,984 B left), the 13th: INSERT SAVE DISK then DISK FILE ERROR, nothing left behind, fsck clean (`f4_full_box1/3.png`); write-protected save disk (`--protect-floppy on`): DISK FILE ERROR, no AES alert, 0 log errors (`f6_wp_result.png`).
  The critic-handler stub is therefore verified on the floppy driver. Untested: floppy on ST TOS 1.04 / Mega STE TOS 2.06 (PP's floppy loader itself fails on 2.06 per `release.md`).
* **Falcon (item 7)**: unsupported, refused cleanly. [disasm] HAGA's swap-in (`HAGA+$1166`) handles machine type 5 (TT) with table entries 0 / 2 (`$200001`, `$1`, `$128a`..`$12c0`) but type 4 (Falcon) with entries `+$c0` / `+$c8` (`$200009`, `$19`) of another table. [obs] with the refusal removed and the TT alias, the Falcon call dies (Hatari log: `Bus Error reading at address $67f60010, PC=$e0fbd2` repeated, TOS 4.04 variables garbage, `fal1.log`), so the TT remap is not the Falcon's. [obs] the shipped blob on a Falcon (TOS 4.04, GEMDOS drive): SAVE -> DISK FILE ERROR box, OK, the game keeps running, 0 log errors, nothing written (`fal3_err.png`). Not pursued further.

## 2. Gates on the final source (HD media; every cell: save T1, T2, overwrite T1, directory shot, LOAD T2 / T1 byte-compared to RAM at the save, LOAD missing name -> box -> OK -> cancel -> running, then 30 calls in a row)
All `RESULT ... PASS`, 0 bus/address-error lines, 30/30 calls ok (cell output delivered in the run, not all kept as files; per-cell Hatari logs `r3_*.log`):
| cell | result [obs] |
|---|---|
| STE 2 MB TOS 1.62, GEMDOS drive | `r3_hd_ste`: PASS |
| Mega STE 4 MB TOS 2.06, GEMDOS drive | `r3_hd_mste`: PASS |
| TT 4 MB TOS 3.06 (`--mmu true --monitor vga --cpuclock 32`), GEMDOS drive | `r3_hd_tt`: PASS, directory lists T1 T2 |
| Mega STE, ACSI + HDDRIVER image | `r3_acsi_mste`: PASS |
| TT, ACSI + HDDRIVER | `r3_acsi_tt`: PASS, directory lists T1 T2 |
| STE, ACSI + HDDRIVER | `r3_acsi_ste`: loop 30/30, all later checks PASS; the very first save's dump was missed by the debugger breakpoint (the file on disk is 56,690 B; the overwrite of the same name is byte-exact). `cell_main.py` now repeats a save whose dump was missed; `r_acsi_ste` earlier today (same blob minus floppy/TT code) had that first dump and PASSed |
Negative control for the raw-trap design (earlier, Pop2Save2): `neg_raw.txt`.

## 3. Level / error gates
* `cell_level.py` (STE hd): 1. save right after the world loaded: file == RAM; 2. LOAD then at once QUIT MAP -> new conquest world: in_play, 4 `$140` data calls; 3. save right after the second world: file == RAM, differs from the first; LOAD world 1 into world 2's session: RAM == saved. All true.
  Step 4 (RESTART MAP right after a LOAD) first run failed because the harness did not click PROCEED on the game's battle-settings screen (`rs1_after.png`); fixed; interactive PROCEED works (turn 74, running). The full cell rerun `lv2_hd_ste` was still running when I stopped: **open**.
* Full disk on HD (ACSI): `cell_err.py --kind full` needs `size_mb=8` (mkfs.fat refused a 4 MB FAT16 with 2-sector clusters) and the OK y=184 fix: **not run**. The floppy full-disk case is covered above.

## 4. Open items: ALL CLOSED 2026-11-13 (Pop2SaveClose; outputs `work/gates/save_*.txt`; the list below is the history)
1. `lv2_hd_ste` (level step 4) and `cell_err.py --kind full` on ACSI not finished.
2. **`p2tick.py ab`, `p2abtest.py` and `p2noquest.py` regressions with the save patches in the default set were NOT run.**
3. HD write-protect (`--protect-hd on`) and floppy on other TOS versions not run.
4. `tools/package.sh` not run; `PATCHES.TXT` still says in-game save does not work (text to put in, once defaults flip: "In-game SAVE GAME / LOAD GAME work on ST/STE/Mega STE/TT, files NAME.GAM 56,690 B in FILES\ or the typed drawer; complete on disk when the game returns to play; not on the Falcon (DISK FILE ERROR; use the HAGA statesave)"; `FLOPPY.TXT` already has the save-disk section; `package.sh` and `pop2patch.py build --floppy` already ship/build `Populous2_save.st`). `README.md` / `PLAN.md` / `patches/README.md` still say save is unsupported / list `pop2_save_a/b`.
5. Hatari quirk for tests: the ST floppy image is only written to the host file on eject (`--disk-a other.st`).
