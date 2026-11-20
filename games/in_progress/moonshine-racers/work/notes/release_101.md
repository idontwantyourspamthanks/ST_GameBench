# Moonshine Racers v1.0.1 release record (MSRRelease101)

Bug fixed: v1.0 `ta_nomouse` skipped the IKBD mouse query whenever `$1021 == 2`, which also holds in the post-race shop and on title/Ike screens (frozen pointer, EXIT unusable). v1.0.1 (commit `9493139`) gates on the stock race flag `$1028` (blob at `$BE500`: `4a38 1028 6702 4e75 4ef9 0000 d138`: `tst.b $1028.w / beq.s .q / rts / .q: jmp $d138.l`).
Raw outputs, scripts and screenshots: `work/pkg101/` (`gate.py` full/pace cells, `psg.py`, `credit.py`, `run_all.sh`, `*.txt` logs, `credit_*.png`). Hatari 2.6.1, private HOME, one Hatari at a time.

Build note: the clean worktrees lack git-ignored build inputs; copied (real dirs, ignored by git) `work/dumps` and `work/floppy` from the main tree into both worktrees; `build --zip` without a path writes into the worktree's `dist/`, so an explicit zip path was always given. Worktrees stay clean (`git status`: only the `alt`/`originals` symlinks untracked). `{GIT}` = `git rev-parse --short HEAD` + a "+ uncommitted" note only when `git status --porcelain -- patches tools` is non-empty; the untracked symlinks are outside those paths, so the stamp is clean.

## 1. Reproduction proof (worktree `80b98f9`, built to /tmp/msr101/v10 vs shipped v1.0 zips)
Rebuilt zips are byte-length equal to the shipped ones (HD 1,083,079 / floppy 915,921). Every member md5 equal to the shipped v1.0 except the README/PATCHES `build:` line (the shipped zips say `git a6f87f7`, the rebuild `git 80b98f9`; `diff` shows that single line only):

| member | shipped v1.0 md5 | rebuilt `80b98f9` |
|---|---|---|
| HD `FILES/MS1` `FILES/MS2` `FILES/MSR_S1.FIC` `FMR273.HST` `HAGA` `LMR273.HST` `LOG.TXT` `MR240R.BMP` `PATCHES.TXT` `RUNME.TOS` | 1966ed9d / cc3ff529 / ab06c5b4 / c6666560 / 59083376 / ee11982c / 43a55230 / d0862c9d / efc94f06 / 22aa2d76 | equal (10 of 11) |
| HD `README.TXT` | ca9aa4d9 | 92a76f41 (stamp line only) |
| floppy `disk_a.st` `disk_b.st` | 31e29c6a / 0d0be455 | equal |
| floppy `README.TXT` `PATCHES.TXT` | 044e8293 / 3f7881b7 | 43b5c14b / 79a9ee45 (stamp line only) |

So the committed sources at `80b98f9` are the v1.0 sources.

## 2. v1.0.1 build (worktree `9493139`)
Built twice (`b1`, `b2`): all member md5s identical (diff -r of the unzipped trees empty). The zip files themselves differ in 22 bytes (zip entry timestamps), md5 b1 HD 18db60b9 / b2 73df50a4, b1 floppy 1e19cd46 / b2 661a1173; contents identical. README stamp `build: git 9493139`, no `-dirty`.
Member diff v1.0 -> v1.0.1 (HD): `RUNME.TOS` 22aa2d76 -> 7c1e3629 (294 differing bytes in the packed file: the blob and the credit text), `README.TXT`, `PATCHES.TXT` (version strings, credit text, ta_nomouse description, stamp, README v1.0.1 note); all other 8 members equal. Floppy: `disk_a.st` 31e29c6a -> e3ae53dc, README/PATCHES; `disk_b.st` equal. `git diff 80b98f9 9493139`: `patches/VERSION`, `ta_nomouse.s` (cmpi.b #2,$1021 / bne -> tst.b $1028 / beq), README_HD/FLOPPY v1.0.1 note: nothing else.

Delivered (copies of b1): `dist/MoonshineRacers_hd_v1.0.1.zip` 1,083,171 B md5 `18db60b970148561e0c3d5046a079f26` sha256 `e61fcc149627aa43825ec2ce79c902b4fb39795a6f891e91201fc00cf82b17d0`; `dist/MoonshineRacers_floppy_v1.0.1.zip` 916,014 B md5 `1e19cd46c0d9d93d043fa7e281360fa0` sha256 `a28a270424f86784a925658a0fd6f859f1f3e0936c7138521dbeb89317751911`. v1.0 zips untouched (1afefab5 / 9c07c7c9). Unzipped members: HD RUNME.TOS `7c1e3629f06be7b3ebb4d253a5c8dd3d`, README `b1558a67`, PATCHES `2e57c394`; floppy disk_a.st `e3ae53dcd0f4d3f719ff244039b98a8b`, disk_b.st `0d0be455e4d0389ed98401c0e02d21d9`.

## Why gating on $1028 is safe
Scan of every absolute-short `$1028` operand in the game RAM dumps (`work/dumps/ram_race0/race_up/entry`, capstone): writers `$72c0 st.b $1028.w` and `$72d0 clr.b $1028.w` around `jsr $76f4` (the race call: `$72c4 jsr $76f4.l`, `$72ca clr.w $91f0.l`, `$72d0 clr.b $1028.w`, then `$72d6 jsr $d82c`); the only reader besides our blob is `$11f8a tst.b $1028.w / beq.b $11f9a / move.w $102c.w,d2 / move.b $11fae(pc,d2.w),$11aa.w`, i.e. inside the race setup/loading code it only selects a byte from a table at `$11fae` indexed by the level/base `$102c` when the flag is set, else leaves the value already stored to `$11aa`; it does not copy, store or clear the flag and does not run on title/shop screens (`work/notes/trackloader.md` row `$11f90`). (Other `1028` byte matches in the dumps are `movep`/`cmpi.w #$1028` data, not `$1028.w` operands.) Observed in Hatari (gate cells): `$1028 == 0xff` during race 1 and race 2 on every machine; `$1028 == 0` on the title/story samples and in the shop (`$1024 == 0xff`, `$1021 == 2`); it becomes 0xff again when race 2 starts. (During the first ~800 VBL after EXIT the flag read 0xff while `$1024` was still 0xff = the race call has started.)

## 3. Gates on the shipped v1.0.1 zips (b1 unzipped to /tmp/msr101/s1; `gate.py`)
Common per cell (all True/as listed): boot_to_race (criterion `$23c0 != 0`, `$1024 == 0`, `$1021 == 2`, `$100e > 30`), marker `MSPO`; race 1 mouse test (pin pointer, `hatari-event mousemove` +100,+100): pointer variables `$6100..$6117` unchanged = FROZEN, `$1028 = 0xff`; finish race 1 by BAR poke (`$133a` stream, `00 1a`, `$6105 = 01`) -> `$1024 == 0xff` -> shop; in the shop `$1028 = 0`, same mouse test: pointer variables CHANGE (x/y `0064 0064`, MOVES); pointer at EXIT (0,167) (`$6106 = 0000 00a7`) + click -> `$1024` goes 0, `$100e` restarts at 0, race 2 starts (RACE2 started True); race 2 mouse test FROZEN, `$1028 = 0xff`; then 16 MHz window and 300 s of play with `$6105 = 01` (hatari alive, no crash).

| cell | boot vbl | title/Ike pointer (`$6106` before -> after +40,+20) | race 1 mouse | shop mouse | EXIT -> race 2 | race 2 mouse | race 2 16 MHz window | 300 s play | Bus/Addr lines |
|---|---|---|---|---|---|---|---|---|---|
| HD STE 1 MB TOS 1.62 | 6515 | `0028 0014` -> `0050 0028` (moves) | FROZEN | MOVES | True (vbl 12430 -> 12937) | FROZEN | 506 VBL, 101 passes (0.1996/VBL), extra 286 | alive | 3 |
| HD STE 4 MB | 6514 | same, moves | FROZEN | MOVES | True | FROZEN | 506 VBL, 101 passes, extra 294 | alive | 3 |
| HD Mega STE 1 MB TOS 2.06 (60 Hz) | 6727 | same, moves | FROZEN | MOVES | True | FROZEN | 606 VBL, 101 passes (0.1667/VBL), extra 137 | alive | 0 |
| HD ST 1 MB TOS 1.04 | 6515 | same, moves | FROZEN | MOVES | True | FROZEN | 506 VBL, 101 passes, extra 284 | alive | 5 |
| floppy STE 1 MB, disk-2 swap into A (lone disk_a.st, prompt at vbl 2895) | 3910 | samples at vbl 1898/2264 read `00000000` (not seen moving: see unproven) | FROZEN | MOVES | True | FROZEN | 506 VBL, 102 passes, extra 295 | alive | 2 |
| floppy STE 1 MB, disk 2 inserted into drive B at the prompt | 3909 | idem | FROZEN | MOVES | True | FROZEN | 505 VBL, 101 passes, extra 282 | alive | 2 |

(An earlier floppy run, `f_fl`/`f_flB`, was invalid for the swap/drive-B routes: Hatari auto-inserted `disk_b.st` next to `disk_a.st`, so no prompt appeared (= the "disk 2 in B from power-on" case); results equal; the cells above were rerun with a lone `disk_a.st` and are the swap/insB routes. `f_fl.txt`/`f_flB.txt` are kept in `work/pkg101/` and are that startB variant.)

### Credit (screenshots read)
`work/pkg101/credit_hd_vbl2551.png` (HD, STE boot) and `credit_fl_vbl673.png` (floppy): hot-rod title picture shows `v1.0.1 enhanced by dad_prg` under the picture.

### Race pace v1.0 vs v1.0.1 (pace-only cells, race 1 from the first race frame with `$6105=01`; windows ~505 VBL native then 16 MHz; passes = `$100e`, extra = `$b8f38` frame counter; same boot, same script)
| cell | v1.0 native | v1.0.1 native | v1.0 16 MHz | v1.0.1 16 MHz |
|---|---|---|---|---|
| HD STE 1 MB | 505 VBL, 101 passes, extra 71, fps 17.030 | 506, 101, 71, 16.996 | 506, 101, 157, 25.494 | 506, 101, 156, 25.395 |
| HD STE 4 MB | 506, 101, 71, 16.996 | 506, 101, 71, 16.996 | 505, 101, 157, 25.545 | 506, 101, 157, 25.494 |
| HD Mega STE (60 Hz) | 608, 101, 111, 20.921 | 606, 101, 110, 20.891 | 607, 101, 104, 20.264 | 607, 101, 103, 20.165 |
| HD ST 1 MB TOS 1.04 | 505, 101, 67, 16.634 | 506, 101, 67, 16.601 | 506, 101, 153, 25.099 | 506, 100, 152, 24.901 |
| floppy STE (startB variant) | 506, 101, 70, 16.897 | 505, 101, 70, 16.931 | 506, 101, 157, 25.494 | 505, 101, 157, 25.545 |

Pace is equal within window quantisation (1 pass / 1 extra frame). The package.md numbers (28.4 fps at 16 MHz) used a later window; same-script v1.0 is the baseline here (25.4).

### Bus/Address Error lines (Main's check)
v1.0 baselines from the same pace cells (v1.0 shipped zip, boot + two windows; `run_p0_*/log.txt`): STE 1 MB 3, STE 4 MB 3, Mega STE 0, ST 5, floppy 2; v1.0.1 pace cells and the 300 s gate cells give the same counts; the `diff` of the quoted lines (v1.0 pace cell vs v1.0.1 gate cell) is empty for STE 1 MB, ST and floppy. All lines are at boot (hardware probes), none during play, none new from the patch. Actual lines: STE (1 MB/4 MB): `Bus Error reading at address $ffff8e21 PC=$21238`; `$ff8e21 PC=$b4928`; `$ff8e21 PC=$bf6b2`. ST: `$ffff8e21 PC=$21258`; `$ffff8924 PC=$21286`; `$ff8e21 PC=$b4928`; `writing $ff8a28 PC=$b494c`; `$ff8e21 PC=$bf6b2` (STE-only registers probed on a plain ST). Floppy: `$ff8e21 PC=$b4928`, `$ff8e21 PC=$bf6b2`. Mega STE 0. (integration.md 12.15 explains the STE ones.)

### Strict PSG gate (strict Hatari, `sound=True, trace_psg=True, strict=True`; boot to race + 40 s drive)
- HD STE 1 MB: `PSGCHECK run_psg_hd: PASS (violations 0, warnings 0; reg-7 writes 2923, reg-14 writes 312, FDC commands 18, selects 44286, data writes 44284, frames 5, frames with reg 7 bits 6/7 not both set 0 (longest run 0), final reg 7 = $fa)`
- floppy STE 1 MB, disk-2 swap into A (lone disk_a): `PSGCHECK run_psg_fl2: PASS (violations 0, warnings 0; reg-7 writes 1636, reg-14 writes 172, FDC commands 589, selects 28943, data writes 28941, frames 1477, frames with reg 7 bits 6/7 not both set 0 (longest run 0), final reg 7 = $fe)`
- (also, floppy with disk 2 auto-inserted in B: `run_psg_fl: PASS ... FDC commands 590, frames 1393, final reg 7 = $fa`.)

## Unproven
- Real hardware: nothing run on a real ST/STE/Mega STE; the only real-machine evidence is the user's MiSTer confirmation of the v1.0 bug (not of the fix). TT/Falcon not run.
- Floppy title/Ike-screen pointer: the three samples I took on the floppy (vbl 1510/1898/2264) were taken before any pointer screen and read zeros; the title/Ike pointer is shown moving only on the HD cells (mouse query gating is the same blob in both builds, `$1028 == 0` was read on the floppy title samples). The shop pointer and EXIT on the floppy are proven.
- Floppy pace cell and floppy title samples were taken with disk 2 auto-inserted in B (pace is unaffected by the disk route; no pace cell was run on the swap route).
- Mega STE floppy not run; 5 min of play is race 2 with auto-drive only (no input other than `$6105 = 01`).
- Shop reached by poking the BAR object, not by finishing a race by driving.
