# Moonshine Racers: campaigns in the FLOPPY release (MSRCampFloppy, 2026-11-20)

Research + scratch prototype; nothing under `patches/`, `tools/`, `core*.s`, `dist/`, `originals/` was edited. Scratch, scripts, logs, proposed diffs: `work/campfloppy/`.
Machine for every run: Hatari 2.6.1-devel (`~/Code/AtariST/hattari/build/src/hatari`), private `HOME=/tmp/msrcf_home` (`work/campfloppy/run_env.sh`), one Hatari at a time, harness `tools/stharness.py` via `work/campfloppy/cf.py`. Game = the floppy build built fresh into scratch (`tools/msrpatch.py build --floppy --out work/campfloppy/build`, public tree; the integrated tests use `buildcamp`, section 7). Disk reads use **real FDC timing** (`hatari-option --fastfdc no` set before the read; boots run with fast FDC).
Tags: **[obs]** raw output kept under `work/campfloppy/logs/` (file named); **[INFERENCE]** not proven; real hardware / MiSTer were NOT tested anywhere.
Companions: `trackloader.md` (stage 2, redirect sites A-D), `trackformat.md` (campaign file / disk), `floppy.md`, `floppy_driveb.md`, and MSRCampHD's `patches/cp_*.s` (HD menu, as they stood at 12:20-12:31, see section 7).

## 0. Result in one page

| # | question | answer |
|---|---|---|
| 1 | RAM size / 2 MB gate on the floppy | TOS' `$42e` is **wiped** by the original stage-1 loader (VBL 99) and is 0 at the hook; `$ff8001` (MMU memory config) is readable and gives `$05 / $08 / $0a` for 1 / 2 / 4 MB on ST, STE and Mega STE. **Recommended gate: the boot-sector (stage-0) loader copies `$42e` to `IB+4` before the game's loader runs; `core_floppy.s` gets MSRCampHD's two-list table with `phystop >= 2 MB` as its only gate.** Built and gated live on 1/2/4 MB (section 1.3). Free RAM above 1 MB in a floppy race: **all of `$100000-$1FFFFF` (2 MB STE) / `$100000-$3FFFFF` (4 MB) is zero and untouched, also while driving**; Mega STE 2 MB: `$100000-$1F81FF` (a 13 KB TOS 2.06 island at `$1F8200-$1FB7FF`). Better than the HD build (no HAGA/TOS copy at the top), so the HD constants (`HIMEM_END = $1CD000`) are safe for both. |
| 2 | reading a campaign from a disk | **Works with the game's own FDC driver, no new disk format.** The driver takes the track length from the HIGH word of its device word (9..11, else 10), so the 720 KB / 9-sector FAT12 disk of `msrtrack.py disk` is read as it is. Reader = BPB -> root directory -> `MSTRACKS.TRK` -> linear sector reads (428 + 126 B; the file is contiguous by construction). Stock-size campaign (64,676 B) **4.3-4.7 s** (drive A, drive B, two-drive), maximum file (123,496 B) **8.2 s**, Mega STE 4 MB 5.4 s; byte-identical read-back in every run; the game keeps running (VBL handler ran every frame, keyboard IRQ serviced mid-read) and asks for disk 2 itself afterwards. |
| 3 | swap UX / errors | campaign disk goes in drive A or B (menu items), no automatic probing; a disk-present probe (port of `fl_driveb`'s `bpres`) turns "no disk" into **1.9 s** instead of the driver's 13 s; wrong disk 0.3 s, blank disk 0.4 s, truncated 0.8 s; retry on the same drive reads anyway (13.2 s) in case the probe is wrong on some hardware. Disk 1 is never read after the title, so no "insert disk 1" step exists; with the campaign disk left in A the game's own "Insert Disk 2" prompt appears at the first race. Two-drive route (disk 2 in B from power-on, campaign disk in A): no prompt at all, race starts. |
| 4 | design / cost | **The cp_* patches of MSRCampHD port with ~10 changed lines + the reader**: sites A-E and menu, validator and CRC code are build-independent (byte-identical at all five sites in the floppy RAM, and proven live: campaign loaded from a floppy, custom track and base-level swap raced, section 7). Floppy-specific code = the reader (~830 B) in place of the HAGA reader. Payload image: **0 extra sectors** (109 before and after: it fits the gaps). Proposed edits: section 8 (`work/campfloppy/proposed/*.diff`, all `patch --dry-run` clean against the tree of 13:02). |

## 1. RAM size and the 2 MB gate (question 1)

### 1.1 What the floppy stub sees
* The original stage-1 loader (relocated to `$7f830`) clears `$400-$66000` at VBL ~99: a change-watch on `$42e` fired there, `pc=$7f89a` (`dbf` of the clear loop), `$42e` = 0 afterwards [obs `logs/e1c_ste2m.txt` first run]. At the hook instant (trampoline `$b2708`, `fl_hook`) every TOS variable is gone [obs `logs/e1c_matrix.txt`]:
```
STE 2 MB      $42e=0 $424=00 $436=0 $2dc=0 $5a0=0   $ff8001=08   SR=$2304   (VBL 2005)
STE 4 MB      same                                    $ff8001=0a
Mega STE 2 MB same                                    $ff8001=08
ST 4 MB       same                                    $ff8001=0a
```
* No HAGA (`$2dc` = 0): the HD gate's machine-type byte does not exist either.
* `$ff8001` at VBL ~370 on every machine x size [obs `logs/e1b_matrix.txt`]: ST / STE / Mega STE: 1 MB `$05`, 2 MB `$08`, 4 MB `$0a` (bits 3-2 = bank 0, bits 1-0 = bank 1: 0 = 128K, 1 = 512K, 2 = 2 MB).

### 1.2 Options
1. **Stage-0 capture of `$42e` (recommended).** The boot-sector loader runs before the original loader wipes low RAM and sees TOS' authoritative phystop (the HD gate uses the same variable). One instruction `move.l $42e.w,$b2704.l` (8 B, the boot sector has 180 B free: 118 B used of 298) after the payload is read. The trampoline reads `IB+4`, then clears it, and uses the same byte as the HD "list 2 applied" flag. Works wherever TOS boots the disk (STE, Mega STE, ST with TOS 1.04, MiSTer, any TOS that sets `$42e`).
2. `$ff8001` in the trampoline (no boot-sector change): `move.b $ff8001.l,d0 / andi.b #$0c,d0 / cmpi.b #$08,d0`. Works in Hatari on all three machines; [INFERENCE] relies on the register being readable on real hardware and on the MiSTer core (not verified), and does not see the odd 512K+2M layout. Fallback only.
3. A memory probe at `$1FFFFC` etc. is rejected: unpopulated RAM bus-errors on an ST and the trampoline has no bus-error vector.

### 1.3 Built and gated live (private build, section 8 edits)
[obs `logs/q2_e6_*.out`, first title loop `$7242`]
```
machine           RAM   $b2700   IB+4 flag   sites $74fe/$7252/$72c4/$77da/$fda2/$731e   F10 at the title
STE TOS 1.62      1 MB  MSPO     00          all stock bytes (4fef000e6106 ... 0c40000f6408)   game starts like any key ("Insert Disk 2" prompt reached)
ST  TOS 1.04      1 MB  MSPO     00          stock                                              same
STE               2 MB  MSPO     ff          all six redirected (jmp/jsr into $b8xxx/$b9f00)    campaign menu
STE               4 MB  MSPO     ff          same                                               menu
Mega STE 2.06     2 MB  MSPO     ff          same                                               menu
ST  TOS 1.04      4 MB  MSPO     ff          same                                               menu
```
* **1 MB A/B**: no gated site is touched; the only bytes that execute beyond the stock path at 1 MB are the stage-0 `move.l` (8 B) and the trampoline's gate test (cmpi/scc/clr/tst/beq). RAM `$1000-$B26FF` at the first title loop, public floppy build vs the gated build, STE 1 MB: 59 bytes differ in 13 runs, all in `$507b3-$50878` and `$77f61-$7ffef` (the game's work area and the stack below `$80000`); the ST 1 MB run differs in the same two windows [obs inline, snap dumps deleted, `e6_gate.py`]. [INFERENCE: stack/work-area values, not decoded; the code and data of the game are identical.] The formal A/B state gates (`msrabtest.py`) were NOT run.
* **ST with 2 MB+**: the floppy gate is RAM only (the build has no machine-type test; the ST TOS 1.04 4 MB cell above opens the menu). The user's "STE / Mega STE only" cannot be enforced without a new probe; a 2-4 MB ST is [INFERENCE] fine (nothing in the feature is STE specific). Decision for the lead; a TOS-version test (`$e00002 >= $0106`) would be the cheap STE filter [INFERENCE, not tried].

### 1.4 Free RAM in a floppy race [obs `logs/e3_*.txt`, `logs/zeromap_*.txt`]
Cold boot, SPACE to the game's "Insert Disk 2" prompt, disk 2 swapped into A, race at the standing start ($1021 = 2, `$23c0 = $58c14`), and again after 25 s of driving ($5ff8 = 2488 / 1881); `savebin` of all RAM, 512-byte zero map:
```
STE 1.62 2 MB   $0d9200-$1fffff zero (1179 KB); 0 non-zero 512-B blocks in $100000-$1FFFFF, start and driving
STE 1.62 4 MB   $0d9200-$3fffff zero (3227 KB); $100000-$3FFFFF zero, start and driving
Mega STE 2.06 2 MB   $0d7200-$1f81ff zero (1156 KB), island $1f8200-$1fb7ff (13 KB, TOS 2.06), $1fb800-$1fffff zero; $100000-$1F7FFF zero, start and driving
```
So the HD map (`$100000-$1CD7FF`) is a subset; the 4 MB machines have `$200000-$3FFFFF` as well. No HAGA, no TOS copy.

## 2. Reading the campaign file (question 2)

### 2.1 Why the game's own driver reads the existing disk
* Sole entry `$d6fa` -> `$cac0` (`floppy.md` section 2): `d0` = device word (bit 0 unit, bit 2 side 1), `d1` = sector **within the side** (< 800 for 10 spt), `d2` = count, `d3` = 0 read, `a0` = buffer; result `d0 = 0` ok. **[disasm] `$cac4-$cae4`: `swap d0; cmp.w #9; blt ->10; cmp.w #$b; ble ok`: the high word of `d0` = sectors per track when 9..11, else 10.** The game always passes 0 (10 spt); the 9-sector TOS format of `msrtrack.py disk` is therefore read by passing 9. The driver splits a read at track boundaries but never crosses sides, so the reader makes one call per track side (LBA -> `side = (lba/spt) & 1`, `track = lba/spt/2`, `d1 = track*spt + lba%spt`).
* [obs] a 9-spt 720 KB image reads byte-identically (`logs/e2_stock_A.txt` etc.): no 10-spt disk variant is needed; one campaign disk image serves both releases (the HD build's TOS reader reads the same file).
* DMA to `$110000+`: the driver stores the DMA pointer in 24 bits; fine to 4 MB [obs 2 MB and 4 MB].

### 2.2 Disk layout / what the tool must guarantee
`msrtrack.py disk` already writes the file in consecutive clusters from cluster 2 (`build_disk`, "contiguous clusters from 2"), first root entry the volume label, second `MSTRACKS.TRK`. The reader (`campread2.s`, 428 B + `rdsec` 126 B):
1. boot sector (LBA 0): bytes/sector `$0200`, spt 9..11, spc, reserved, FAT count, sectors/FAT, root entries -> root LBA = `res + nfat*spf`, data LBA = root + `(ndir+15)/16`;
2. root directory sector by sector (stops at the first free entry, 1 sector in practice), 11-byte name `MSTRACKSTRK`, skips deleted / label / directory entries; first cluster and size;
3. `lba = data + (cluster-2)*spc`, size <= max, one `$cac0` call per track side into the destination.
The **FAT chain is not followed**: a fragmented file would read the wrong clusters and fail the header/CRC check of the shared validator. **Proposed guarantee**: `msrtrack.py` `disk_read_file` (used by `validate X.st`) refuses a non-contiguous chain with a clear message (`proposed/msrtrack.py.diff`, tested on the three disks: stock 64,676 B, max 123,496 B, a 3-track campaign; and on a hand-fragmented image: `E-DISK: ... is not stored in consecutive clusters (cluster 2 is followed by 4)`). The header check itself (`MSTK`, count, length, table CRC, per-block CRC) is MSRCampHD's `validate`, shared (it runs on the file in `CPSTORE`).

### 2.3 Results [obs `logs/e2_*.txt`, `logs/e5_*.txt`, `logs/q1_*.out`]
Cell: floppy build booted to the title, prototype blob (`campread.s`, F10 hook, prompts) loaded by the debugger at the first title loop, F10, campaign disk swapped into the chosen drive with `hatari-option --disk-a/--disk-b`, key A/B, `savebin` of `$110000` after the read.
```
cell                                   file                 read time (50 Hz VBL, real FDC)   status   read-back
STE 2 MB, campaign disk in A           stock 15 tracks 64,676 B   4.68 s (VBL 2682 -> 2916)    0       identical (md5 3f5462fa...), count 15
STE 2 MB, campaign disk in B           same                 4.48 s                                 0       identical
STE 2 MB, two-drive (disk 2 in B from power-on), campaign disk in A   same   4.32 s               0       identical
Mega STE 4 MB, in A                    same                 5.42 s                                 0       identical
STE 2 MB, in A                         max 15 x 8192 B = 123,496 B   8.16 s                        0       identical (md5 c8283838...)
STE 2 MB, in A, key SPACE sent 2.5 s into the read   same as first   4.46 s                          0       $60ff = $39 right after the key: the keyboard IRQ was serviced mid-read
```
(`dpres` + boot sector + root directory are inside these numbers: the wrong-disk cases below cost 0.3-0.4 s in total, so the file read is ~4.2 / ~7.8 s: ~15 KB/s.) Real hardware has the same rotational structure (one revolution per 9-sector track side plus a seek); [INFERENCE] 4-6 s for a stock-size campaign.
**Interrupts / music**: the game's VBL handler (`$d11e`, which calls `$d486`) keeps running during the read. The `mt_clock` long `$b8f00` (+6 per VBL at 50 Hz) advanced by `$53a` = 1338 = 223 x 6 over the 223 VBLs of the read [obs `logs/e5_vblclk.txt`]. The FDC wait loops of the driver poll GPIP with interrupts enabled, exactly as in the game's own race load. Sound itself was not listened to [INFERENCE: the music routine runs from the same handler].
**Game resumes** [obs `logs/e2_stock_A.txt`]: after the read the title runs again; SPACE -> the game's own `Insert Disk 2 and press a key.` prompt appears (the campaign disk is still in A: its boot sector fails the game's `$d788` check, offset `$e` is not `$66055505`) -> disk 2 swapped in -> `$1021 = 2`, `$100e` 501 -> 547, prompt gone, `$b2700` = `MSPO`.
**No disk-1 reads after the title** [obs `logs/e8_reads.txt`]: breakpoint on `$cac0` from the first title loop to the disk-2 prompt: **one** driver call (`d1 = 0`, `d2 = 1`, the boot-sector check). So the campaign disk replaces disk 1 for good: nothing needs "Insert Disk 1". (Consistent with `floppy_driveb.md`: whole-run drive-0 read counts = 1127 boot + 100 race + check reads.)

## 3. Swap UX, errors, interaction with disk 2 / drive B (question 3)

### 3.1 Flow (as built in the port, section 7)
`F10` at the title -> campaign menu (HD agent's menu) -> `LOAD CAMPAIGN FROM DRIVE A` / `... DRIVE B` (a hint row says `INSERT THE CAMPAIGN DISK, THEN CHOOSE`) -> `LOADING CAMPAIGN FROM DRIVE A...` -> `CHECKING CAMPAIGN...` -> track list -> `Play from track N`. Nothing is read before the user chooses (no automatic probing); the earliest failure is reported on the menu's message row.

### 3.2 Error paths [obs `logs/e5_ste2m.txt`, `logs/e5b_retry.txt`; every one returns to the prompt, no hang]
```
case                                  status          camp_read time
game disk 2 in A (wrong disk)         3 not FAT       0.30 s
blank DOS disk in A                   4 no file       0.44 s
random bytes in A                     3               0.26 s
truncated image (200 KB, valid BPB)   2 read error    0.82 s
drive B empty (drive present)         1 no disk       1.90 s
drive A ejected                       1 no disk       1.90-2.08 s
same drive again after a status 1     2 (forced read) 13.18 s   -> then OK with the right disk: 4.40 s
```
* **Disk-present probe** (`dpres`, 140 B): the logic of `fl_driveb`'s `bpres` for either drive (restore with h=1 must reach TR00 without seek error within ~1.2 s, then an INDEX pulse within ~1.5 s; deselect). Without it a drive without a disk sits in the driver's own bounded waits (`$60000 / $60000 / $40000` loops = 13 s in Hatari, `floppy_driveb.md` section 5). [INFERENCE] it assumes real drives and Gotek/MiSTer images give index pulses while selected (same assumption `fl_driveb` makes; not verified on hardware).
* **Retry reads anyway**: if the previous attempt on the same drive returned status 1, the next one skips the probe and lets the game's driver try (13 s worst case): a hardware where the probe is wrong is not locked out after one failed attempt. The cost is only paid by a user who retries an empty drive.
* Messages in the port: no disk / not a FAT floppy / no `MSTRACKS.TRK` all show `NO CAMPAIGN DISK IN DRIVE A|B`; read error `DISK READ ERROR`; too big `CAMPAIGN FILE IS TOO BIG`; everything wrong with the content is the shared validator's (`NOT A VALID CAMPAIGN FILE`, `... DAMAGED (CRC)`). Finer messages (wrong disk vs empty) are possible: the reader has the codes.

### 3.3 Interaction with disk 2 and `fl_driveb`
* The reader calls `$cac0` directly with its own unit; it does **not** touch `fl_driveb`'s `unit` / `pref[]` (those only change inside the game's disk checks at `$d6fa`), so `fl_driveb` stays optional (it is `default: yes` but removable with `--only`); the driver's per-unit head table `$cfac` is shared and kept consistent by the driver itself.
* One drive: the campaign disk is inserted in A at the title and left there; the game's check of disk 2 fails, shows its prompt at the first race, the user swaps disk 2 [obs]. Two drives, disk 2 in B from power-on: campaign disk into A: the game's check reads A (campaign disk: mismatch), B (disk 2: match): **no prompt, race starts in 22 s wall** [obs `logs/q1_twodrive.out`: `'Insert Disk 2' prompt ever shown: False`, `$100e` 69 -> 115, `MSPO`]. Campaign disk into B replaces disk 2: the next race check mismatches on both drives and shows the prompt (disk 2 back into either drive) [logic, not run].
* The campaign stays in RAM after a game over (the title returns, `V_ACT` stays) until the user chooses `ORIGINAL GAME`; loading a second campaign works the same (F10 again; `e2 --twice` was not run).
* While loading, keys pressed are still queued by the IKBD handler; the menu will see them afterwards [obs: `$60ff` = `$39` mid-read]. Cosmetic.

## 4. Cost, design, risks (question 4)

### 4.1 Shared vs floppy-specific
```
shared, build independent (MSRCampHD's cp_* as they stand)          floppy specific
cp_wrap $72c4, cp_fetch $77da, cp_ptr $fda2, cp_end $731e,          the reader behind trk_read: camp_read 428 B, rdsec 126 B,
cp_start $7252, cp_hiscore $8418: original bytes identical in        dpres 140 B, adapter ~80 B, vars 28 B  = ~830 B
work/floppy/ram_answered.bin [obs] and in the floppy RAM at the      core_floppy.s: two-list table + phystop gate (1.2)
hook instant (e6 above: the five sites read stock at 1 MB)           msrpatch.py: floppy table, stage-0 capture
cp_title menu, list screen, CRC-32, validate (`$74fe` site)         3 item strings + 4 messages (drive A/B instead of hard disk/A)
CPV/CPWORK/CPSTORE/CPTAB layout ($b8e00, $100000..$12ffff)           nothing: all free in the floppy race (1.4)
```
The HD agent's HAGA reader (`trk_read`, ~900 B: part A + the `bstart` template) is simply not assembled for the floppy; the floppy `trk_read` has the same contract (`a0 = path, a1 = dest, d1 = max -> d0 = 0 / GEMDOS-style error, d1 = bytes`; the first letter of the path, `A:` / `B:`, selects the unit), so `load` is unchanged.

### 4.2 Recommended design
1. `core_floppy.s` = the HD core's two-list structure, gate `IB+4 >= $200000` (phystop copied by stage 0); `msrpatch.py` floppy builds accept `; gate: ram2mb` patches, the floppy table gets the same `(n+2)*16` layout. The cp_* patches lose `; media: hd` and build in both; `cp_title.s` is built per flavour. Cheapest way without two copies of 889 lines: split the build-specific tail of `cp_title.s` (the reader + the 8 strings) behind `ifne FLOPPY` with `FLOPPY` predefined by `msrpatch.py` like `CP_EQUS` (the tool must then assemble each patch once per build flavour in `verify`); or a separate `cp_rdhd.s` / `cp_rdfl.s` pair behind a fixed `CPREAD` entry. `proposed/cp_title.s.diff` is the flavour diff (620 lines, almost all the removed HAGA reader).
2. Stage-0 gets `move.l $42e.w,$b2704.l`.
3. `msrtrack.py disk_read_file` refuses a fragmented file (section 2.2). The 720 KB disk stays as is (also works for the HD release).
4. Docs: README_FLOPPY.TXT / PATCHES_FLOPPY.TXT: F10 at the title, 2 MB+ only, insert the campaign disk before choosing, disk 2 prompt as usual.

### 4.3 Cost (agent-hours, estimate)
Floppy gate + stage 0 + table: 1.5 h (done as scratch); reader + adapter: done as scratch (3 h spent; ~1 h to harden: messages, `e2 --twice`, 800K/880K disks); `FLOPPY` flavour split of cp_title + msrpatch verify per flavour: 2 h; gates on the floppy (1 MB A/B state gates on 1 MB ST/STE, 2/4 MB STE and Mega STE cold boot into a campaign race, restart / time-out / finish / ending on the floppy, two-drive, a real swap with `--fastfdc no`): 4 h; docs 1 h = **about 8-9 h** on top of MSRCampHD's work, i.e. well under the study's 8-10 h estimate because the menu and hooks are shared.
Code size: +~830 B in the payload, **0 additional disk sectors** (109 sectors before and after: [obs] `payload 55348 B (109 sectors)` public tree and private tree with all cp_* patches; the blobs fall into the gaps of the existing image).

### 4.4 Risks
1. **Real hardware / MiSTer untested** (index pulses for `dpres`, real FDC timing of a 9-sector disk through the game's driver, whether the high-word geometry path of the driver was ever exercised by the original game: it passes 0). The forced retry covers a wrong probe; a wrong geometry path would show as status 2/3.
2. `$42e` stage-0 capture assumes TOS booted the disk (true for every boot of this release); TT/Falcon not run.
3. ST with >= 2 MB opens the menu (decision for the lead, 1.3).
4. 4-8 s load window with the game running; keys pressed during it are queued.
5. Fragmented user-made disks (PC tool re-copy) fail with "not a campaign" unless the tool's `validate` was run; mitigated by the proposed tool check and by the CRC.
6. 1 MB A/B (state gates) not run on the floppy; only the site-byte and RAM-window comparisons of 1.3.
7. The 13 s forced-retry path and the MiSTer assumptions are unverified outside Hatari.
8. MSRCampHD's files are in flux: the port is regenerated by `work/campfloppy/portfl.py` from the CURRENT `patches/cp_*.s` (last tested snapshot = identical to the tree of 13:02: cp_title.s 889 lines, six more files).

## 5. Prototype descriptions
* `campread.s` / `campread2.s` (v2 = forced retry): standalone blob at `$100000`: `camp_read(d0 unit, a0 dest, d1 max, d2 force)`, `rdsec`, `dpres`, `showtext`/`waitkey`/`camp_ui` (own prompts: `LOAD A CAMPAIGN / Insert the campaign disk, then press A for drive A, B for drive B, ESC to cancel.`), F10 hook at `$7252`. Used by `e2.py`, `e5.py`, `e5b.py`.
* `camphooks.s` (hooks A-D for the real MSTK file format, debugger-loaded): superseded by the real cp_* patches in section 7, kept as scratch; `e7_race.py` was not run.
* `portfl.py` + `priv/` (private `msrpatch_priv.py`, `priv/patches/` = current `patches/` + the floppy `core_floppy.s` + ported `cp_*.s`): builds the integrated floppy image with `CF_PATCHDIR=work/campfloppy/priv/patches python3 work/campfloppy/priv/msrpatch_priv.py build --floppy --out work/campfloppy/buildcamp`.

## 6. Raw results: E5/E2 key lines
```
e2_stock_A:   VBL at entry/exit: [2682, 2916] => read time 4.68 s; status d7 0; v_count 000f v_size 0000fca4; read-back compare 64676 B at $110000: identical=True
              game's own 'Insert Disk 2' prompt shown: True; race after disk 2: $1021=02 $100e 501 -> 547; prompt gone: True; marker $b2700: b'MSPO'
e2_max_A:     [2679, 3087] => 8.16 s; 123496 B identical
e2_stock_B:   4.48 s identical;  e2_twodrive: 4.32 s identical, no prompt, race $100e 69 -> 115;  e2_mste4m: 5.42 s identical, prompt, race $100e 504 -> 550
e5_ste2m:     [0] 0.30 s st3  [1] 0.44 s st4  [2] 0.26 s st3  [3] 0.82 s st2  [4] 1.90 s st1  [5] 1.90 s st1  [6] ok 4.64 s, mid-read $60ff = 39
e5_vblclk:    $b8f00 0x0e1c -> 0x1356 (= 223 x 6), VBL delta 223
e5b_retry:    [0] ejected A 2.08 s st1  [1] same drive again 13.18 s st2  [2] empty B 1.90 s st1  [3] good disk 4.40 s ok
e8_reads:     1 driver call between the title and the disk-2 prompt (d1 = 0, d2 = 1)
```

## 7. The integrated port: campaign loaded from a floppy and raced [obs `logs/e9_*.txt`, screenshots `logs/e9_*_N*.png`]
Private build `buildcamp` (STE TOS 1.62, 2 MB, boot with fast FDC, real FDC for the read): cold boot, title, F10, menu (`e9_base5_t0_2sel.png`: `ORIGINAL GAME / LOAD CAMPAIGN FROM DRIVE A / ... DRIVE B / BACK TO THE TITLE`, highlighted row, hint rows), Down, Return with `camp5_720.st` (3 tracks: 0 = stock level 5, 1 = EDIT1 custom on base 0, 2 = stock level 2) in A, track list, `Play from track N`, SPACE through the title/map to the game's `Insert Disk 2` prompt, disk 2 swapped in, standing start; `$b2700` = `MSPO`, IB+4 = `ff`.
```
play from track 1:  V_ACT ff, store head 4d53544b00010003, $102c = 5 (BASE 5 during the race), POS 0, $57890.len 18000 (= level 5), stream pointers $23c0 = 001100a8 ... inside the store
                    curve ring $1bbc first 1024 words == decoded curve of the stock level-5 block: True; drove 12 s ($5ff8 1293); $1024 := $ff -> $102c = 0001 (position 0 restored, +1 by the campaign loop)
play from track 2:  $102c = 0 (base 0), POS 1, $57890.len 19472, $23c0 = 00111066 ... (inside the store), curve ring == decoded curve of the custom EDIT1 block: True (first diff None);
                    drove 12 s ($5ff8 1157, $130c 10); race screenshot e9_edit_t1_6race.png: normal HUD and road; $1024 := $ff -> $102c = 0002 (position 1 + 1)
```
So on the floppy build: the campaign read from a floppy, the position/base swap (A), the track fetch redirect from RAM above 1 MB (B, C), the restore for the campaign loop and the validator all work with MSRCampHD's code unchanged except `trk_read` and the item strings. (The `loaded (wall 60 s)` poll in the log waits for `V_LOADED == 1` but the patch stores `$ff`: a harness slip, not a game delay.) Not run on the floppy port: end-of-campaign site D with count < 15 live (bytes verified only), time-out replay, ending, `Original game` after a campaign, hi-score F10 (`$8418`).

## 8. Exact proposed edits (all against the tree of 2026-11-20 13:02; `patch --dry-run` clean)
Files in `work/campfloppy/proposed/`:
* `core_floppy.s` (whole proposed file) and `core_floppy.s.diff`: HD core structure (two lists, `verify` / `apply`), gate = `cmpi.l #$200000,MARKER+4.l / scc d0 / clr.l MARKER+4.l / tst.b d0 / beq.s .g / lea TABLE2.l,a5`, `st MARKER+4.l` when list 2 was applied, exit = the displaced `move.l #$6f5a,$88.w / trap #2`.
* `msrpatch.py.diff` (27 lines): (a) remove the "gated patch cannot be part of a floppy build" refusal; (b) `tbl_len = (n + 2) * 16` for both builds; (c) stage-0 loader `.done:` gets `move.l $42e.w,$b2704.l` (assembled from `IB + 4`); (d) docstring.
* `cp_wrap/cp_fetch/cp_ptr/cp_end/cp_start/cp_hiscore.s.diff`: delete `; media: hd` (these build in both flavours).
* `cp_title.s.diff`: delete `; media: hd`; menu strings `t_hd/t_a/m_ldhd/m_lda/e_nf/e_nfa/p_hd/p_a` -> drive A / drive B; `FL_FAIL equ CPWORK+$2B0` + `clr.w FL_FAIL.l` in `cp_menu`; hint row `t_ins` ("INSERT THE CAMPAIGN DISK, THEN CHOOSE") at row 20; the HAGA reader section replaced by the floppy `trk_read` + reader (`camp_read`, `rdsec`, `dpres`, `vars`, `fname`). Apply as a flavour (`ifne FLOPPY` / two files) rather than as one file replacing the other.
* `msrtrack.py.diff`: `disk_read_file` refuses a non-contiguous FAT chain.
* Docs (not drafted): README_FLOPPY.TXT / PATCHES_FLOPPY.TXT (F10 at the title, 2 MB+, campaign disk in A or B).
Not proposed: any change to `fl_driveb`, `fl_hook`, `fl_deprot`, `core.s`.

## 9. Files (for the lead to commit)
New: `work/notes/campaign_floppy.md`. New under `work/campfloppy/`: `cf.py run_env.sh portfl.py q1.sh q2.sh`, `campread.s campread2.s camphooks.s`, cells `e1_probe.py e1b_matrix.py e1c_hook.py e2.py e3_ram.py e5.py e5b.py e6_gate.py e7_race.py e8_reads.py e9_integ.py`, `priv/msrpatch_priv.py priv/patches/` (a full copy of `patches/` with the proposed floppy core and the ported cp_*), `proposed/*`, `logs/*` (outputs and screenshots; the E3 zero maps `logs/zeromap_*.txt`), `disk/*.trk *.st ring_*.txt`.
Regenerable, do not commit: `build/`, `buildcamp/` (floppy images), `*.bin`, `*.lst`, `disk/*.st`, `priv/patches/` is a copy (regenerate with `portfl.py` + copying `patches/`); the 21 MB RAM dumps were deleted after zero-mapping.
Reproduce: `cd games/in_progress/moonshine-racers; python3 tools/msrpatch.py build --floppy --out work/campfloppy/build; work/campfloppy/run_env.sh python3 work/campfloppy/e2.py stock_A --camp work/campfloppy/disk/stock720.st --trk work/campfloppy/disk/stock.trk --key A` (disks: `msrtrack.py campaign new ... --stock; msrtrack.py disk`).
