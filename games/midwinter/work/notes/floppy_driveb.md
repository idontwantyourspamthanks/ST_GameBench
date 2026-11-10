# Midwinter 1 floppy: graphics disk (MWB) in drive B (2026-11-10)

Report (real MiSTer ST core, patched floppy set): the game asks for the graphics disk, MWB goes into drive B, the text darkens, nothing loads.
Tools: `tools/m68dis.py`, `games/midwinter/tools/mw1flopb.py` (new: Hatari 2.6.1 cells with drive-B modes, raw FDC timing, `--bp` debugger hits),
`tools/mw1patch.py build --floppy`. Patch: `patches/floppy_driveb.s` (`media: floppy`, **`default: no`**). [INFERENCE] marks what was not proven.
Companion notes: `floppy.md`, `loading.md`; Midwinter 2: `games/midwinter2/work/notes/floppy.md`.

## 1. Result in one paragraph

Not a regression of our patches: **the original Midwinter 1 only ever reads drive A.** Three immediate `move.w #2,$134(a6)` (`$10334`
save-disk reader, `$10CEA` file loader `sub_010cd2`, `$10F22` writer) are the only writers of the drive word; `sub_011344` turns it into
PSG port-A select bits (2 -> A, 4 -> B) and nothing ever sets 4. There is no disk label check: the loader xor-16-checks every file against
its directory entry and on a mismatch (or read error) draws the retry page (dark text) and waits for a key. MWB in drive B therefore
produced the dark retry page forever; drive B's LED never lit. Midwinter 2's *original* loader flips A<->B itself (section 6); I mirrored
that in `floppy_driveb` for MW1 (A first, B only on a failed check, bounded probe, A's/B's FDC track bookkeeping, save disk stays on A).
Tested in Hatari with real FDC timing; not tested on a MiSTer or a real ST.

## 2. Reproduction (Hatari, real FDC timing = `--fastfdc no`)

`python3 tools/mw1flopb.py NAME MACHINE TOS 1024 DISKDIR MODE` with the **release** zip images (`dist/Midwinter_patched_floppies_2026-11-10.zip`
unpacked to `/tmp/drvb`) and with the original `FILES/MWA`, `MWB`. Modes: `swapA` (drive A -> MWB at the prompt), `insB` (MWB inserted into
drive B at the prompt), `startB` (MWB in B from power-on), `none`, `lateswapA`. Screens: bright prompt = waiting for the first key; after the
key the game tries the load, fails, and shows the same text **dark** (colour 5, drawn by `sub_010db8`).

```
rel_swapA_ste   STE 1.62  release  swapA   Options reached at 66 s                                        (works, as floppy.md)
rel_insB_ste    STE 1.62  release  insB    prompt seen, NOT reached in 300 s: dark prompt, B LED never on
rel_startB_ste  STE 1.62  release  startB  NOT reached in 142 s (dark prompt)
rel_insB_st104  ST  1.04  release  insB    NOT reached in 134 s
orig_insB_ste   STE 1.62  FILES/MWA+MWB insB  NOT reached in 150 s            (original game: same failure)
orig_insB_bp    breakpoints $10D1A (check failed), $10DB8 (retry page), $11370 (PSG select write):
                $10D1A and $10DB8 hit 11x each, $258A2 = $2590C (MWB table), file number $2F (47 = first MWB load);
                all 7 $11370 hits have D7 = $25 (A selected). Never $23 (B).
```
"Text darkens" = the first key press makes the game start loading from A (still holding MWA), the check fails and the retry page is drawn in
the dim colour; it loops on every further key. In the swap-A route the same dim page appears for a moment when the key is pressed before the swap.

## 3. How the original loader works (disassembly of `FILES/MWA` sector 195 -> `$7E4`)

```
010cd2 sub_010cd2 (25 callers)  movem; $62b8 saved; a6=$2C376
010cea   move.w #2,$134(a6)           <- drive A (only writer besides $10334 / $10F22)
010cf0   bsr $11344                   ; select: d7 = $134(a6); not.b d7; andi #7; PSG reg 14 |= d7  (2 -> %101 = A side 0, 4 -> %011 = B)
010cf4   bsr $10e1c                   ; seek (track = (start-1)/10) + read (sub_0110ae: DMA, unbounded wait on GPIP bit 5, $112CA)
010cf8   cmp.b #$80,d0 ; beq $10d14   ; status $80 = motor on, no error.  else restore ($11016), re-read once
010d14   bsr $10d78 ; beq $10d6c      ; xor-16 of the loaded words vs directory entry word 4 ($258A2 -> table)
010d1a   error: numbers via $10da8, sub_010db8 = "Insert graphics disk / Press any key when ready" (colour 5), key, bra $10cf4
010d6c   success exit (the deferred-patch hook site, unchanged)
```
Which disk is wanted is only `$258A2`: `$2590C` = MWB table, `$258A6` = MWA table (`$100C6` / `$100E2`). The file loader never re-selects the drive
between retries (only at entry), so the drive word is "A". Strings: `Insert game data disk` ($10759), `Press any key when ready`, `Insert graphics disk`,
`Insert main disk`, `Please insert a disk holding saved games in drive A` ($1066x): the game itself says drive A.
Save/load menus: `$FAE0` (save) and `$FC18` (load) are routines of the in-game menu; both do `$1011E` (prompt "Insert game data disk"), `$10030` (restore +
read sector 1 of A, refuse a disk whose first word is `$0008`/`$603A`), directory from sector 2 (`$12345678` magic, `sub_00ffa0`) and finish with
`$100C6` + `$10172` (re-selects the MWB table, prompt "Insert graphics disk") + `jmp $2D74`. MWC sector 2 carries the magic and 2 saved games.
Identification of the disks is by the directory only; for reference the boot-sector serial (bytes 8-10): MWA `000123`, MWB `1115B2`, MWC `C3BE86`.

## 4. The patch (`floppy_driveb`, site `$10CEA`, 130 bytes -> `jmp $B9400`, blob `$B9400-$B97FF`)

Mirrors Midwinter 2 (section 6) under Main's constraints:
* **One-drive behaviour = original.** Drive A: `move.w #2,$134(a6); jsr $11344; jsr $10e1c; ...` the same calls in the same order; the blob adds a `clr.w`
  and a `tst.w` (not measurable: key -> Options 14 s with and without it). Only a failed file check for the **graphics disk** (`$258A2 = $2590C`) reaches new code.
* **Failed check -> probe the other drive once, before the prompt.** `probe`: switch drive (select via `$11344`), restore on first use (`$11016`, bounded), seek 0
  (`$1102E`), read sector 1 (`$110FE`, whose wait `$11302` is bounded: `$40000` loops, then force interrupt `$D0`), up to 2 tries into a 512-byte blob buffer.
  Success needs status `$80` **and** the DMA pointer moved by 512: a forced interrupt also leaves status `$80` (found the hard way, section 5), so status alone
  said "OK" for an empty drive B and the unbounded full read hung. The restore must also reach TR00 without seek error (a drive that does not exist, or MiSTer's
  drive without an image, reports a seek error / RNF). If the probe fails the old drive is re-selected and the original retry page follows. If it passes, the file
  is re-read in full from the other drive (original `$10E1C` path, xor check). On success `pref` = that drive: later graphics loads start on it, so no failed read from A.
  If the preferred drive later fails, the same logic tries the other one (A <-> B symmetric, MW2: `eori.w #6,$27d34`).
* **FD1772 track register bookkeeping.** One controller, one TR, two heads. On every drive change the blob stores TR for the drive left and loads the stored head
  position of the drive entered (first use: restore). After a load from B it switches back to A with A's TR, so every other part of the game (save/load menus, which seek
  relative to TR, always drive A) sees the original state. (Hatari models each drive's physical head; MiSTer's `fdc1772.sv` derives the SD LBA from the TR register
  (`sd_lba = fd_spt*track[6:0] ...`, line ~108/121), so it would not even notice a mismatch. A real ST would.)
* **Save disk (MWC) stays on A.** `$10334` and `$10F22` untouched (drive A). TOS drive count (`$4A6`) is **not** used as a gate: on MiSTer a drive B image mounted after
  power-on is not seen by TOS [INFERENCE from the core: TOS probes B at boot; a drive without an image returns RNF], yet the user inserts MWB into B at the prompt.
  The bounded probe covers the missing-drive case instead.
* Variables in the blob (`cur`, `pref`, `tried`, `known[2]`, `pos[2]`) are initialised by the image; `mw1flopb.py` prints them (`m $B9602`): after a B boot
  `cur=0 pref=1 tried=0 known=1,1 pos=$3C,$3E`; after an A boot all zero but `known=1,0` (nothing touched).
* Known limits: a read from a drive whose disk vanished mid-load is unbounded like the original (Hatari hangs on an ejected drive, MiSTer returns RNF after 6 ms);
  the retry page after a failed B probe takes longer (below); the 3 `$134(a6)` writes elsewhere are not changed.

## 5. Test matrix (Hatari 2.6.1, real FDC timing, 1 MB, raw outputs `/tmp/drvb/q_*.out`; "key->Options" from the first key press, 2 s polling)

Build `fl_db2` = `floppy_secbypass floppy_driveb`; `fl_db_all` = all 55 default patches + `floppy_driveb` (`verify: ALL OK`, no site/blob overlap).
```
cell                      machine/TOS   build      mode        result
m3_swapA                  STE 1.62      fl_db2     swapA       Options, key->Options 14 s, blob state untouched (cur 0 pref 0 known 1,0 pos 0,0)
m8_rel_swapA              STE 1.62      release    swapA       Options, 14 s                       (unpatched control, same time)
m1_insB                   STE 1.62      fl_db2     insB        Options, 16 s, pref=1, PSG select $23 (B) x6, $25 (A) x13 ($11370 breakpoint log v1_insB_psg)
m2_startB                 STE 1.62      fl_db2     startB      Options, 16 s, pref=1
t1_insB_st104             ST 1.04       fl_db2     insB        Options, 16 s, pref=1
t2_startB_st104           ST 1.04       fl_db2     startB      Options, 16 s, pref=1
t3_insB_mste              MSTE 2.06     fl_db2     insB        Options, 16 s, pref=1
t5_startB_mste            MSTE 2.06     fl_db2     startB      Options, 16 s, pref=1
m5_none_noB               STE 1.62      fl_db2     none, --drive-b false (ONE drive)   dark retry page 7 s after the key (original build 5 s), no hang
m7_late_noB               STE 1.62      fl_db2     lateswapA, one drive    dark page, A -> MWB, key: Options 22 s after the first key
m4_none_emptyB            STE 1.62      fl_db2     none (B present, empty)  dark retry page 12 s after the key (b1_rel_none original: 5 s), no hang
m6_late_emptyB            STE 1.62      fl_db2     lateswapA, empty B       Options 27 s after the first key
t4_late_emptyB_st104      ST 1.04       fl_db2     lateswapA, empty B       Options 27 s
f1_all_insB / f3_late_emptyB / f4_swapA (STE 1.62), f2_startB (ST 1.04)   with the 55 default patches + floppy_driveb: Options 16 / 27 / 14 / 16 s
```
Overhead only on a failed check for MWB: +2 s (no drive B) / +7 s (B present, empty) before the retry page; swap-A and correct-disk-in-A flows are unchanged.
Earlier mistakes in my own runs, kept for the record: (1) the first probe (status `$80` only) passed on an empty drive B and the full read hung (PC `$112E6`, the
unbounded `$112CA` loop) -> DMA pointer check; (2) `insert_graphics.png` is the DARK page: matching it only after a key press made the first cells look as if the prompt
was never seen (reference of the waiting page: `work/ref/insert_graphics_bright.png`).

### Save / load flows with MWB sitting in B (`--menu`)
At the Options screen `r pc=$FC18` (load) / `$FAE0` (save) enters the menu; at "Insert game data disk" drive A -> MWC (copy), key.
```
s1_startB_load   fl_db2 startB  "Insert game data disk" -> LOAD GAME with Game 0 / Game 1 (read from A after the B loads), same screen as the original
s2_startB_loadback / s3_rel_swapA_loadback  back icon -> "Insert graphics disk" -> key: THE TEAM screen, identical in both (patched: MWB left in B; control: A -> MWB)
s4_startB_save / s5_rel_swapA_save  save slot 0 written to drive A: MWC copy differs from FILES/MWC in 1030 bytes in both,
                                    and the two MWC copies are byte-identical (md5 a61efbdac328e5a560ba351f60532920)
```
Not run: loading a saved game into the 3D view, a save followed by an MWB load (the back flow ends in `jmp $2D74`; no MWB file load happened before THE TEAM).

## 6. Midwinter 2 reference (original loader) and MiSTer

Midwinter 2's own code picks the drive from a word per disk: `sub_02772c` derives `$ee(a6)` from the track-side counter (`/ 80`) OR `[$27D34]`; `$27D30/$27D32` hold the
last drive code (2 = A, 4 = B) of the graphics and the campaign disk; `sub_028b20` reads the disk tag (`$E576` vs the expected string at `[$93CA]`) and on a mismatch does
`eori.w #6,$27d34` (A <-> B) and retries (`dbra d0`, two tries) before it shows "Insert ... Disk"; after a success the code is copied back to `$27D30/32`
(`sub_028a60`/`028aa6`/`028ae6`). That is exactly "try the remembered drive, then the other, then ask", with a per-disk memory: what `floppy_driveb` does for MWB.
(Per Main: MW2 works with two drives on the user's MiSTer; not re-tested here.) MW1 has no disk tag, so the xor-16 file check plays the tag's role; MWC stays A-only.

MiSTer ST core (`MiSTer-devel/AtariST_MiSTer` `rtl/fdc1772/fdc1772.sv`, `floppy.v`, `AtariST.sv`, read from GitHub master 2026-11-10; [INFERENCE] that the user's build matches):
* FD1772 model (`MODEL=2`), status bit 7 = `motor_on`, so the game's `cmp.b #$80` after a read works. Drive select = PSG port A bits 1/2 (`floppy_sel`), A and B both wired
  (`floppy_sel_exclusive`: both selected -> A). **No disk-change or write-protect-change line**: the ST has none and the loader never looks at WP (only writes would see it).
  Nothing in the loader depends on a media-change flag, so no re-read-boot-sector workaround is needed for detection; the xor check is already the detection.
* A drive without a mounted image: Type I and Type II commands set RNF and raise the IRQ after 6 ms (`!fd_present` branches) -> a failed B probe ends quickly and the original
  read loop would not hang there either. The restore passes TR00 (`fd_track0`) but sets RNF = status bit 4, which is why `switch` also checks bit 4.
* Each drive only spins while selected (`motor_on_sel = motor_on && select`, 500 ms spin-up, `ready` only at full rate), a read waits for `fd_ready && sector header` without an RNF timeout:
  the first access after a drive switch just takes up to ~0.5 s; the probe allows two tries anyway.
* The LBA comes from the TR register, not from the drive's head (see section 4), so the TR bookkeeping is harmless there and needed on Hatari / real hardware.

## 7. Open points for the lead

1. Review `floppy_driveb` (default no). To ship: set `; default: yes`, rebuild, and change `FLOPPY.TXT` ("put MWB in drive B ... or swap MWB into A as before; keep the save disk in A").
2. Untested: real MiSTer / real STE; a full play session with saves from B-booted state; fast-FDC; MWC as the save disk in drive B (not supported by design).
3. Optional extension (not done, asks for a decision): route the save disk to B as well (the three `$134(a6)` writes), mirroring MW2's per-disk drive words.
