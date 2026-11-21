# Moonshine Racers: campaigns in the HD build (MSRCampHD, 2026-11-20)

Implements stage 2 of the track editor for the HD release (design: `trackloader.md`, file format: `trackformat.md`, tool: `tools/msrtrack.py`).
Scratch (scripts, logs, screenshots, test campaigns): `work/camphd/`. Tags: **[obs]** raw output kept in `work/camphd/`, **[INFERENCE]** not proven.
Hatari 2.6.1 (`~/Code/AtariST/hattari/build/src/hatari`), private `HOME=/tmp/camphd_home`, builds made fresh with `msrpatch.py build --out work/camphd/<name>` (`b3` = first full build, `b4` = final: ST family gate), never `build/hd`.

## 1. What was built

| piece | file | notes |
|---|---|---|
| E-BAR | `tools/msrtrack.py`, `work/trackedit/test_msrtrack.py::test_bar_rule`, `trackformat.md` section 5 | exactly one object whose base-level type has sprite `$21`; all 15 stock tracks pass; 19 unit tests + `selftest` OK |
| gate | `patches/core.s`, `tools/msrpatch.py` | second site table (`; gate: ram2mb`), verified+applied only when `phystop >= $200000` AND HAGA+`$83` (PP's machine type) is 1 / 2 / 3. Core = 246 B of 248. Marker byte `IB+4 = $ff` when list 2 was applied |
| redirect sites | `cp_wrap $72c4` (A), `cp_fetch $77da` (B), `cp_ptr $fda2` (C), `cp_end $731e` (D), `cp_start $7252`, `cp_title $74fe`, `cp_hiscore $8418` | all `; media: hd`, `; gate: ram2mb`, `default: yes` |
| menu, reader, validator | `patches/cp_title.s` (3,068 B at `$B9F00`) | F10 menu, HAGA-window reader (port of `work/trackloader/trkread.s`), CRC-32 validation |
| tool | `tools/msrpatch.py` | `; gate:`, `; himem:`, `; media: hd`; predefined `CPV CPTAB CPWORK CPSTORE`; HD table = [list 1][zero slot][list 2][zero slot][pool]; `live` and floppy builds exclude gated patches |
| docs | `patches/README.md` (Campaigns section), `patches/README_HD.TXT`, this file | |

HAGA+`$83` measured [obs] (`work/camphd/boot_b4_*.txt`, `probe_st2m.txt`, `probe_mst2m.txt`): ST TOS 1.04 and Mega ST TOS 1.04 = **1**, STE = **2**, Mega STE = **3**, at 2 MB (`$2dc=$1F8000`) and 4 MB (`$3F8000`). Gate open (marker `4d53504f ff`, sites changed) on all eight cells ST/Mega ST/STE/Mega STE x 2/4 MB. TT (5) and Falcon (4) are outside 1..3 [type values: reader refuses 4; TT/Falcon probe `log_probe_tt.txt`, `log_probe_falcon.txt` if the chain reached them, see section 5].

## 2. Budget and RAM map

* Payload image unchanged: **55,348 B** (`$B2700-$BFF33`), cap `$F000` = 61,440 B (headroom 6,092 B), because all campaign code sits in zero gaps of the existing image: hooks `$B8022-$B8069` (A), `$B8070-$B80C1` (B), `$B8220-$B823F` (D), `$B8240-$B825D` (start), data `CPV $B8E00-$B8E1F`, `cp_title` `$B9F00-$BAAFB` (3,068 B = menu 1.5 KB + validator/CRC + reader 0.8 KB + strings). `cp_title` declares `conflicts: mx_pre mf_pre sb_bar` (their data/blobs lie in `$B9F00-$BAFFF`).
* RAM above 1 MB (at 2 MB; same at 4 MB): `$100000-$1003FF` CRC table, `$100400-$1007FF` menu scratch, `$110000-$12FFFF` campaign file (max 123,496 B), HAGA top region from `HAGA+$3900` (reader part B, installed on first load). Everything stays below `$1CD000`.
* `verify` ALL OK; no pair overlaps; footprints printed by `python3 tools/msrpatch.py list`.

## 3. Behaviour

* `ACT` (campaign selected), `LOADED`, `COUNT`, `POS`, `START`, `PTR` live in `CPV`. Race wrapper (A): with `ACT`, `POS := $102c & $f`, `$102c := base level of entry POS` for `jsr $76f4`, afterwards `$102c := POS | (flags the race set)`. Fetch (B): `PTR := CPSTORE + entry.offset`, `clr.b $C0008` (rd_geom reuse); without `ACT` the stock load and `PTR := $58c00`. C: `movea.l PTR,a0`. D: `cmp.w COUNT` (15 without `ACT`). `$7252`: `Play from track N` sets `START`, `$102c := START` after the stock `jsr $73b8`.
* F10 = scancode `$44` in `$60ff`, hooked at the title's shared key exit `$74fe` (two stack depths: 14 bytes in the sprite loop, only the return address `$7246` in the final wait loop, where the original `lea $e(a7),a7` pops 14 too many; the F10 path tests this and does not pop) and the hi-score screen exit `$8418`. Menu: `ORIGINAL GAME`, `LOAD CAMPAIGN FROM HARD DISK` (`FILES\MSTRACKS.TRK`, relative to HAGA's current directory), `LOAD CAMPAIGN FROM DRIVE A` (`A:\MSTRACKS.TRK`, only on request), `LOADED CAMPAIGN: N TRACKS` (track list `PLAY FROM TRACK`, `< BACK`), `BACK TO THE TITLE`. Text with the game's own routine `$12268` (the font has no descenders: all menu text and track names are shown in capitals), selection = inverted row, headings yellow. Keys up/down, Return/Enter/Space, Esc/Backspace/Left, joystick up/down/fire.
* Validation (in the game, before anything is used): magic, version 1, count 1..15, file length, table CRC-32, per entry flags 0 / base < 15 / contiguous offset / even length 2..8192 / name characters, block CRC-32, no bytes after the last block. A new load first clears `ACT`/`LOADED`. Messages: `MSTRACKS.TRK NOT FOUND IN FILES`, `NO CAMPAIGN DISK IN DRIVE A`, `NOT A VALID CAMPAIGN FILE`, `CAMPAIGN FILE IS DAMAGED (CRC)`, `CAMPAIGN FILE IS TOO BIG`, `DISK READ ERROR`, `FILE ACCESS NOT AVAILABLE HERE`.

## 4. Gate results (b3/b4 builds, Hatari; raw logs `work/camphd/log_*.txt`, `fin_ste2m.txt`, screenshots `work/camphd/snap/*.png`)

Scripts: `title_snap.py`/`probe_type.py` (cold boot to the title, memstate), `gate.py` (scenarios from the memstate: finish, drivea, errors, timeout, stock), `ab1mb.py` (1 MB gate), `e2e.py`, `mkcamp.py` (test campaigns: `camp/c3.trk` three custom tracks with the BAR moved to unit 700-900, `c15.trk` stock, `bad_*.trk`, `*.st` disks).

* **Cold boot, gate real** [obs] `boot_b4_*.txt`: ST/Mega ST/STE/Mega STE at 2 and 4 MB: marker `MSPO`, `IB+4=ff`, `HAGA+$83 = 1/1/2/3`, all campaign sites patched.
* **STE 2 MB, HD copy, 3-track campaign** [obs] `fin_ste2m.txt` (b3): load 2.6 s; race 1 = custom edit1 track: `$23c0=$1100ac` (inside the store), `ptr=$110088`, `$57890=19472` (base level 0), BAR reached, `$102c 0 -> 1`; race 2 starts with entry 2: `ptr=$111742`, `$102c=3` (base 3), `$57890=19000`; race 3: `ptr=$11283e`, `$102c=5`, `$57890=18000`; after the 3rd finish `$102c=2` (position restored) and the ending runs; the next SPACE at the title starts the campaign again at entry 1 (`$23c0=$1100ac`, `ptr=$110088`): the campaign stays selected after its ending.
* **STE 2 MB, campaign disk in drive A** [obs] `log_drA_ste2m.txt`: `c3.st` inserted with `hatari-option --disk-a` (a memstate restore forgets `--disk-a`), loaded in 5.6 s, track 1 race from the store (`$23c0=$1100ac`). Without the disk the menu said `NO CAMPAIGN DISK IN DRIVE A` (screenshot `drA_ste2m_2_list.png`).
* **Errors and recovery, STE 2 MB** [obs] `log_err_ste2m.txt`: missing HD file, `bad_crc.trk` (message `CAMPAIGN FILE IS DAMAGED (CRC)`, screenshot `err_ste2m_bad_crc_msg.png`), `bad_magic.trk`, `bad_table.trk`, `bad_short.trk`: each rejected with a message; choosing `ORIGINAL GAME` then starts the stock game (`act=0`, `ptr=$58c00`, `$23c0=$58c14`, `$57890=19472`). Further cases in the log (empty drive A, damaged disk) as far as the chain got.
* **Not run / not complete** (the request budget ended the run): see section 5.

## 5. Unproven items and known problems

* **v1.0 shop bug (not campaign-specific)**: ta_nomouse freezes the mouse pointer in the spare-parts store (`$1021` is 2 there), so a race cannot be followed by the next one in v1.0. Reported to the lead (hotfix v1.0.1 planned: `tst.b $1028.w` instead of `cmpi.b #2,$1021.w`). All my multi-race gates therefore **skip the shop** with a debugger breakpoint (`b pc=$725c` then `r pc=$7262`, `gate.py skip_shop`); after the hotfix they must be re-run with the real EXIT click (my xdotool/Hatari mouse clicks did not reach EXIT: with the mouse query restored by hand the pointer moved but stopped about 20 px above EXIT; not resolved).
* Cells with a real run: STE 2 MB (HD 3 tracks + ending, drive A, errors). Cells with only the cold-boot gate proof (marker, sites, type byte): all other ST/Mega ST/STE/Mega STE x 2/4 MB. Cells the chain was started for but that were not completed when this note was written: see `work/camphd/log_*.txt` for whatever finished (`fin_*` = one custom track from the HD copy per cell, `drA_*`, `to_ste2m` = time-out replay, `stock_ste4m` = 10 minute stock race, `ab1m_*` = 1 MB A/B, `probe_tt/falcon`).
* 1 MB A/B (`ab1mb.py`: marker and `IB+4=0`, site bytes, execution breakpoints over the campaign code ranges, per-pass STATE A/B from the v1.0 race memstate with/without the new payload image): script written and syntax checked; **not run to completion by me** unless `log_ab1m_*.txt` exists. By construction at 1 MB `$42e < $200000` skips list 2: no campaign site is written, and the new bytes in the payload are never executed.
* Time-out replay of the same custom track: scenario `timeout` written; not proven by me unless `log_to_ste2m.txt` exists. The replay path is `$102c |= $80` -> `$726c`, which re-enters hooka with `POS = $102c & $f` (design, see `trackloader.md` 4.4: proven with the scratch hooks).
* The title key-exit trick for F10 in the final-wait stack depth was reasoned from the disassembly and not exercised separately; the F10 menu was opened in the face-sprite phase only [obs]; the hi-score screen hook `$8418` is not exercised.
* Real hardware, TT, Falcon, ST/Mega ST TOS beyond 1.04, a campaign file with more than 15 tracks (refused by the format), a disk swap between two loads: untested. Mega STE cache: the reader copies part B into HAGA's top region and executes it; Hatari does not model the Mega STE cache [INFERENCE: Pop2 does the same].
* The F10 menu has a plain black screen (no logo); the title attract loop is restarted after `BACK TO THE TITLE` by re-entering `$73e6`.

## 6. When the gate bytes are sampled (v1.1 release gating, MSRCampaign3)

* **Once, at boot**, by the payload trampoline (`core.s`, the hook instant `pc = $b204e` before the game starts): `cmpi.l #$200000,$42e.w` (TOS' phystop, still intact on the HD build: logs `boot_hd_*.txt` print `$42e=0x200000/0x400000` at the title), then `$2dc.w` = HAGA base and the machine-type byte `HAGA+$83` (PP's HAGA fills it at its own start-up; `$2dc=$1F8000/$3F8000`, byte 1/1/2/3 on ST/Mega ST/STE/Mega STE, 5 on a TT, 4 on a Falcon: `work/campgate/boot_hd_*.txt`, `logs/ttf_hd_*.txt`). Nothing re-reads them later: the result is the marker byte `IB+4` (`$b2704`: 0 closed, `$ff` open) and the applied site bytes. Both bytes are therefore sampled before the game's own loader or any F10 menu code runs.
* **Floppy**: `$42e` is wiped by the game's loader at VBL ~99, so stage 0 (the boot sector) copies it into `IB+4` right after the payload read; the trampoline reads and clears it (0 on TT/Falcon: `_MCH` says not an ST family machine). No machine-type byte exists on the floppy (no HAGA).
* A cold boot is the only point where the gate is evaluated: soft-resetting into a different RAM size or switching to a different machine without a power cycle re-runs the whole boot, so the gate follows it.

## 7. Real-hardware-only risks (nothing below was run on a real machine)

1. **Floppy campaign read**: the game's own FDC driver reading a 720 KB FAT12 disk (one revolution per track side), and the disk-present probe (port of `fl_driveb` `bpres`) that turns "no disk" into ~2 s; Hatari's FDC and index-pulse timing differ from a real drive, a Gotek and MiSTer.
2. **Stage-0 capture** (floppy): the boot sector copies TOS' `$42e` into `IB+4`; on real TOS the variable is set (TOS 1.04/1.62/2.06) [INFERENCE for other TOS versions / MiSTer cores]; `_MCH` is used to leave TT/Falcon at 0.
3. **Mega STE cache with the HAGA reader** (HD): part B of the reader is copied into HAGA's top region and executed; Hatari does not model the Mega STE cache (Pop2 does the same [INFERENCE]).
4. **Real GEMDOS drive-A reads** (HD): `LOAD CAMPAIGN FROM DRIVE A` uses TOS' floppy path with TOS' own empty-drive timeout (empty drive A: 16.9 s on STE TOS 1.62, 5.6 s on Mega STE TOS 2.06, `work/campgate/emptya.py`, `logs/emptya_*.txt`; the PC sits in the TOS ROM loop at $e01742-$e0174c the whole time [INFERENCE: TOS 1.62's floppy select/motor timeout], not in HAGA or the campaign code).
5. The HAGA machine-type byte `HAGA+$83` was measured only in Hatari (1/1/2/3 on ST/Mega ST/STE/Mega STE, TOS 1.04/1.04/1.62/2.06).
