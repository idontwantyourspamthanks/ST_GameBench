# WW1 memory plan: where every blob of the full patch set lives (PMWW1Memory, 2026-11-23)

Design only. Nothing but this file was written in the repo.
Tags: **[obs]** a run / tool output of this session (raw files in `/tmp/pmww1mem/`, listed in section 8); **[master]** measured from master's
Powermonger build or read in its notes (`games/done/powermonger/`); **[stage1/2]** another WW1 note; **[INFERENCE]** reasoning, not run.
Hatari 2.6.1, private HOME, one Hatari at a time, workdir `/tmp/pmww1mem/`. Addresses are WW1 runtime addresses unless marked "master".

## 0. Decisions in one screen

1. **Everything fits on a 1 MB machine, floppy and HD, ST and STE, with no extra left out and no cached resource lost.** One layout for every
   machine and RAM size (as master): the game is position dependent and nothing of ours needs RAM above `$F7000`.
2. **Two areas.** LOW `$72000-$77FFF` (stage 1's payload window) holds the core and ALL code and small state (measured need 14.4 KB of
   22.5 KB). HIGH `$B0000-$F6FFF` (290 816 B) holds ONLY the big buffers: third screen, slope table, DMA staging buffer, interpolation lists,
   sprite cache, HD swap buffer. Code can therefore never be hit by the resource cache, with or without the cap.
3. **Cache cap `CAPLIM = $B0000`** (master: `$B8000`). In WW1 the cache ends at `$AF658` after every resource a normal game can cache
   (map, chart, panel, lose AND win picture) [obs], so the cap costs **0 extra disk reads**; it only stops what was never seen in play
   (the ending files, which are not even on the EA disk). Patch = master's 24-byte hook at site `$e3f2`; run live in WW1 [obs, section 3.3].
4. **Not aligned yet with stage 2**: at 19:37 `RESULTS_stage02.md` has no cache-cap section and `patches/` has no `pm_cachecap.s`.
   Stage 2's own payload (all below `$78000`) does not need the cap. **Request to the lead: if stage 2 adds the cap, the limit must be
   `$B0000`, not master's `$B8000`** (the third screen starts at `$B0000`), and its blob must sit in the LOW area. If stage 2 leaves it
   out, it is stage 4's first work item, before any blob is placed above `$80000`.
5. Proof so far [obs]: pattern over `$B0000-$F7EFF` (and `$F8000-$FFFFF`) **0 bytes changed** through boot, chart, map, save + load,
   lose x2, win x2, a second different land, a random land, 4 lands in all, on STE 1 MB; the same (shorter list) on Mega STE 4 MB and
   ST 1 MB. Not covered: a real battle, the HD build, TT / Falcon, 512 KB (section 7).

## 1. Inventory: what the full feature set needs (sizes measured from master's v1.2 release build)

Source: `games/done/powermonger/build/dist_build/floppy.json` and `hd.json` (`used` spans of the release build, 39 / 44 patches)
[master, read this session]. "disk" = bytes stored in the payload records; "zero" = `; data:` span, zero-filled at boot, no disk bytes.
Master's payload is `$B8000-$EFFFF` for every machine and RAM size; the third screen is outside it at `$70000`.

| blob | bytes | kind | master address | WW1 placement (section 3) |
|---|---:|---|---|---|
| core: entry/init, hooks, apply, site table, init tables, flags, marker | 1 422 (2 048 reserved) | disk | `$B8000-$B87FF` | LOW `$72000-$727FF` (done, stage 1) |
| `tick_head/pass/men/rain` code + D block | 310 + 64 | disk + zero | `$B8800-$B8A3F` | LOW (done, stage 2: `$72900-$72ABF`; `tick_rain` 76 B replaces `tick_wx`) |
| `p3b_interp` + `p3b_delta` code, PD block | 472 + 32 | disk + zero | `$B8A80-$B8C79` | LOW `$73C00` |
| **interpolation lists** OLD (512 x 4) + LST (512 x 10) | **2 048 + 5 120** | zero | `$B8D00`, `$B9500` | **HIGH `$C0000`, `$C0800`** |
| `tt_ptr` (TT / Falcon pointer) | 402 | disk | `$BA900` | LOW `$75800` |
| `hd_core` code (HD only) | 1 564 | disk | `$BB000` | LOW `$77400` |
| **`hd_core` variables + private stack (HD only)** | **4 096** | zero | `$BC000-$BCFFF` | **HIGH `$C2000`** |
| `p4_ptr_a/b` code + P block, `p4_clamp` | 464 + 288 | disk + zero | `$BD000-$BD433` | LOW `$75C00` |
| `p4_spr` code (blitter path + cache path) | 922 | disk | `$BD500`, `$BD700` | LOW `$75C00` range |
| **`p4_spr` pre-shifted sprite cache** (header 1 KB + 8 sets x 6 ways x 1 280 B) | **62 464** | lazy init (magic word) | `$BDC00-$CCFFF` | **HIGH `$DF000`** |
| `pm_tooltip` code / state / wording table | 1 092 / 1 024 / 1 855 | disk / zero / disk | `$CD000`, `$CDC00`, `$CF000` | LOW `$74000` |
| `qol_keys`, `qol_keys2`, `qol_hover`, `qol_hover2` + data | 2 156 + 248 | disk + zero | `$CD460-$CD64D`, `$CF830-$CFFF3` | LOW `$72C00` (keys done, stage 2) |
| `pm_intro_a/b/c/pal` (real-time intro) | 130 | disk | `$CD780`, `$CD800` | LOW `$75800` range (if WW1 has the delay loops at all: it has no separate intro program [stage1]) |
| `pm_credit` | 164 | disk | `$CDB00` | LOW `$72800` (done) |
| `snd_core` code (4 entry points) + SV state | 776 + 64 | disk + zero | `$D0000`, `$D0E00` | LOW `$76400` |
| **DMA staging buffer STAGE** (live resample target; master ships NO sample bank, snd.md 2.1) | **16 384** | zero | `$D1000-$D4FFF` | **HIGH `$BC000`** |
| **`p6_slope` edge-slope table** (64 x 64 longs) | **16 384** | disk in master | `$D5000-$D8FFF` | **HIGH `$B8000`**; generate at init (section 3.5) |
| `p6_tri` code, `p6_cpy` code | 1 902 + 136 | disk | `$D9000`, `$DA000` | LOW `$76800` |
| `p7_triple_wait/flip/tail` code + T block | 144 + 16 | disk + zero | `$DB000-$DB317` | LOW `$77200` |
| **third screen buffer C** (triple buffering) | **32 000** | never initialised | **`$70000-$77CFF`** (not in the payload) | **HIGH `$B0000-$B7CFF`** (WW1's BSS ends at `$71B84`: `$70000` is taken) |
| `fal_ym`, `pm_cachecap`, `pm_mste` | 34 + 24 + 80 | disk | `$DC000`, `$DC100`, `$DC200` | LOW `$75800` range |
| **HD swap buffer S** (TOS's low RAM `R = [$8, BP+$100)`; HD only) | 78 640 (STE 1 MB, TOS 1.62 + HDDRIVER) / 87 760 (Mega STE 4 MB, TOS 2.06) [master loading.md 7.1]; capacity `SMAX` 102 400 | copied by `init` | `$DD000-$F5FFF` | **HIGH `$C3000`**, `SMAX` 114 688 |
| HD overlay window + `PMLATE.DAT` (26 527 B file) | 131 072 (window) | - | `$BD000-$DCFFF` | **not needed** (section 3.4) |
| rain (`tick_rain`), TT / Falcon cache-off, PMMU-off | in `tick_` / core | - | - | LOW, no data |

Totals [master]: code + small state **14 363 B**; big data 32 000 + 16 384 + 16 384 + 7 168 + 62 464 = **134 400 B**; HD adds 4 096 + S.
Master's disk cost: payload records 28 768 B (floppy) / 30 452 B (HD), of which 16 384 B are the slope table.

## 2. What the WW1 game does with RAM (1 MB STE TOS 1.62 unless stated)

### 2.1 Fixed map [obs: 14 RAM dumps `/tmp/pmww1mem/r1/dumps/*.bin`; stage1 `placement.md`, `addrmap.md`]
| range | owner |
|---|---|
| `$500-$575` | the stub's own bytes (master rule: never use) |
| `$576-$1D2AD` | game image (118 072 B) |
| `$1D500-$251FF`, `$25200-$2CEFF` | screen buffers A, B (`[$2ed98]` = L, `[$2ed9c]` = D swap between them at every checkpoint) |
| `$2CF00-$2EDFF` | variables (cache cursor `$2cfda`, pointers, pointer / click words) |
| `$2EE00-$3207F` | TEXTURES (resource 0, destination computed at `$d8d0`: `($2edc0 + $80) & -128`) |
| `$320C0-$4475B` | SPRITE16 `$320c0`, SPRITE8 `$33ec0`, SPRITE24 `$38b3c`, SPRITE32 `$3dbdc` (the `p4_spr` cache key range in WW1) |
| `$4483A-...` | MAP / MAPDATA load buffer; **save state `$44C3E` + `$18C00`** (101 376 B, to `$5D83D`; the sector driver reads / writes it in place, no other buffer [stage2]; the slot's last 10 284 B are the start of FX, static data [INFERENCE from the two addresses]) |
| `$5B012-$71B7B` | FX (resource 9, 93 034 B), then VBL counter `$71b7c`; BSS ends `$71B84` |
| `$71B84-$71FFF` | zero, unused (1 148 B) |
| **`$72000-$77FFF`** | **our LOW area** (free in the original: stage 1 pattern proof) |
| `$78000-$7FCFF` | QAZ picture (resource 1; the frame the window copy `$13a94` takes) |
| `$80000-$AF657` | resource cache (grows once, section 2.3) |
| **`$B0000-$F6FFF`** | **our HIGH area** (free: section 2.4) |
| `$F7FA8-$F7FFF` | 28 non-zero bytes: residue of the start-up stack (1 MB machines), never changes after the hand-over |
| `$F8000-$FFFFF` | TOS's screen RAM on a 1 MB machine; untouched by the game after the hand-over [obs, floppy], not used by this plan |

### 2.2 Phases and the resource loader [obs: breakpoint trace of `$e34c` call / `$e388` not cached / `$e3f8` cache store / `$e42a` return, `r1/events.json`]
Resource table `$e4ba` (12 B: name, destination, size), unpacked sizes `$e476`, file sizes `$e300`, cache pointers `$e432` [obs: read from the
resident image, `tools/m68dis.py work/dumps/entry576.bin e2e2 --end e432`]:

| n | file (on the EA disk?) | file / unpacked | destination | caller | cached? |
|---|---|---|---|---|---|
| 9 | FX.PAK | 75 544 / 93 034 | `$5b012` | boot (VBL 850-1312) | no (before the cache flag) |
| 0 | TEXTURES.PAK | 8 104 / 12 928 | `$2ee00` | `$13ce4` START NEW CONQUEST | no (flag `$e430` still 0) |
| 2 3 4 5 | SPRITE16 / 8 / 24 / 32.PAK | 4 064 / 7 680, 9 432 / 19 580, 8 212 / 20 640, 12 840 / 27 520 | `$320c0..` | `$13cf6-$13d1a` | no (same) |
| 16 | MAPDATA.DAT again (table file size `$418C`; the cache keeps the first 216 B at the destination; the disk load took as long as resource 11's) | 16 780 / 216 | `$4483a` | `$116e0` chart | **yes, 216 B** |
| 10 | MAP.PAK | 38 348 / 65 920 | `$4483a` | `$11706` chart | **yes** |
| 11 | MAPDATA.DAT (whole) | 71 928 / 71 928 | `$4483a` | `$118fc` land start | **never** (file size = unpacked size: `$e3d4 cmp / beq $e42a` skips unpack and cache) |
| 1 | QAZ.PAK | 13 748 / 32 000 | `$78000` | `$14a90`, `$194ac` | **yes** |
| 8 | CAPGRAPH.PAK | 11 672 / 32 000 | `[$2ed9c]` (D) | `$194c8` | **yes** |
| 14 | LOSE.PAK | 24 584 / 32 000 | `[$2ed98]` (L) | `$1b340` Retire | **yes** |
| 15 | WIN.PAK | 12 672 / 32 000 | `[$2ed98]` | `$1b1d6`, `$1b282` | **yes** |
| 12, 13 | END_PIC1.PAK, END.PAK (**not on the EA disk**) | 16 360 / 32 000, 73 872 / 73 310 | L, `$44c3e` | `$1b3b2`, `$1b3cc` ending | would be |
| 7 (6) | BITMAP.PAK (CAP_SPR.PAK) (**not on the disk**) | - / 4 096 | `$4475e` | `$14994` (only if `[$5a9b6] < $100`) | would be |

Caching rule [obs, `$e3ea-$e424`]: after an unpack, if the flag `$e430` is set (once, at `$13d28`, after the first five loads) and the cursor is
non-zero, `size` bytes are copied to `[$2cfda]`, the pointer goes to `$e432[n]`, the cursor advances. A resource is cached once; later calls
copy from the cache (`$e356-$e382`). No bound check, as in master. The RAM probe `$5e8` zeroes the cursor without RAM at `$80000`.
The unpacker `$e69a` works in place and writes exactly `[dest, dest + unpacked size)` (reads the packed stream backwards, writes backwards
from `dest + size`) [obs: disassembly], so a 32 000 B screen buffer needs no margin.

Trace of one session [obs, `r1`, VBL = emulated 50 Hz frames; identical cache addresses on Mega STE and ST]:
```
boot        9 disk 462 VBL
new conquest 0 2 3 4 5 disk (85 65 100 100 119 VBL); 16 disk 194 -> cache $80000; 10 disk 292 -> cache $800d8      cursor $90258 (chart)
land start  11 disk 184; 1 disk 135 -> cache $90258; 8 disk 103 -> cache $97f58                                   cursor $9fc58 (map view)
save + load 1 8 1 8 from the cache (7-9 VBL each); state $44c3e saved == loaded, 0 of 101376 B differ             cursor $9fc58
Retire lose 14 disk 172 VBL -> cache $9fc58                                                                       cursor $a7958
land 2      16 cache (0-1 VBL), 10 cache (16), 11 disk (174), 1 cache (9), 8 cache (8)                             cursor $a7958
Retire win  15 disk 117 VBL -> cache $a7958                                                                       cursor $af658
CONTINUE CONQUEST -> another land (chart click at ST (62,50), north Scotland): 16 10 cache, 11 disk, 1 8 cache     cursor $af658
Retire lose 14 cache 8 VBL;  land 4 (after 'delete conquered lands' YES);  Retire win 15 cache 8 VBL               cursor $af658
PLAY RANDOM LAND: 1 8 cache only (no MAP / MAPDATA load); 2 min idle; an Attack order, 100 s                      cursor $af658
```

### 2.3 The cache cursor's maximum
* **Observed maximum `$AF658`** = `$80000` + 216 + 65 920 + 32 000 + 32 000 + 32 000 + 32 000 (16, 10, 1, 8, 14, 15), reached once both
  Retire pictures were seen; it stays there over 4 lands, a random land and repeated Retires [obs, `r1/run.log`: 8 consecutive
  checkpoints `cursor $af658`]. Map view = `$9FC58` on all three machines.
* **Static bound** [obs for the table and the code path, INFERENCE for "no other caller"]: the loader has 17 call sites
  (`m68dis --callers e344`), listed above; the only resources that can still be cached are 12, 13 (ending) and 7: + 32 000 + 73 310 + 4 096.
  Without a cap the cursor could reach `$CA1B6`; the files for all three are not on the EA disk (`mdir`: 12 data files), so on the
  original disk the game would sit in its "insert disk" requester instead (`$d8c2` retries forever) [INFERENCE, not run].
* The cursor has 5 references (`$5ee $5fa $608 $e3f2 $e424`) [stage1]; the copy loop `$e41e` is the only writer above `$80000` found by
  any run of this session.

### 2.4 Free-RAM proof of the HIGH area (pattern method, the game alone) [obs]
A position-dependent non-zero pattern is loaded by the debugger at the hand-over (`b pc = $576 && ($576).w = $41f9`, `loadbin`), then the
session runs; every checkpoint dumps 1 MB and compares. Build under test: `build/noprot/floppy.st` (stage 2: credit, noprot, nokeydisk;
payload only in `$72000-$728A3`). Raw lines: `/tmp/pmww1mem/<run>/run.log`.

| run | machine | pattern | checkpoints | changed bytes |
|---|---|---|---|---|
| `r1` | STE 1 MB TOS 1.62 | `$B0000-$F7EFF` (294 656 B) + `$F8000-$FFFFF` (32 768 B) | options, chart, map, after save + load, lose 1, map 2, win 1, map 3 (other land), lose 2, map 4, win 2, random land, + 2 min, + Attack order 100 s (14) | **0 at every one** |
| `r2_mste` | Mega STE 4 MB TOS 2.06 (60 Hz) | `$B0000-$FFFFF` (327 680 B) | options, map, lose, map 2, win, random land, lose 2 (7) | **0** |
| `r3_st` | ST 1 MB TOS 1.04 | as `r1` | options, map, after save + load, lose, map 2, win, random land, lose 2 (8) | **0** |
| `r4_cap_a0000` | STE 1 MB, live cap at `$A0000` | `$A0000-$F7EFF` + `$F8000-$FFFFF` | options, map x5, lose x2, win x2 (10) | **0** |

Non-zero RAM between the BSS end and `$B0000` at each `r1` checkpoint: `$72000-$7229B` + `$727F8-$728A3` (payload), `$78000-<cursor>`,
nothing else. Not exercised: a battle (no fight was confirmed; the Attack order's outcome was not checked), the ending, HD, TT / Falcon.

### 2.5 More RAM, HD, 512 KB
* **2 / 4 MB**: the game uses the same absolute addresses (cursor, screens, tables identical on the 4 MB Mega STE run); RAM above 1 MB is
  never touched by it and is not needed by us. On a 1 MB machine the start-up stack and TOS's screen sit at `$F7Fxx` / `$F8000`; on 4 MB
  they are at `$3F7Fxx` / `$3F8000` and `$F7000-$FFFFF` is plain free RAM [obs: whole `$B0000-$FFFFF` pattern intact on `r2_mste`].
* **HD** [master, INFERENCE for WW1]: a resident driver and TOS keep everything in `R = [$8, BP + $100)`, which the game overwrites; `hd_core`
  swaps R with a buffer S around every GEMDOS call. R was 78 640 B / 87 760 B in master's two cells. The high area is inside the program's
  own TPA on every machine with at least 1 MB (TPA = `BP .. $F8000` on 1 MB).
* **512 KB**: the original runs without a cache (probe at `$5e8`); the payload does not: `front` copies to `$72000` and above while the
  start-up stack is at `$77Fxx` and TOS's screen at `$78000`. Needs a guard (work item 2). Not run.

## 3. The layout

### 3.1 LOW area `$72000-$77FFF`: core, all code, all small state (the cache can never reach it: it only grows up from `$80000`)
Proposed prefix contract for `wwpatch.py` (sizes = master's measured blobs; the ranges add up to exactly `$72800-$77FFF`):

| range | bytes | patches | master measured |
|---|---:|---|---:|
| `$72000-$727FF` | 2 048 | core (stage 1) | 1 422 |
| `$72800-$728FF` | 256 | `pm_credit` (done) | 164 |
| `$72900-$72BFF` | 768 | `tick_*` (done; `tick_rain` here) | 374 |
| `$72C00-$73BFF` | 4 096 | `qol_*` (keys done at `$72C00 / $73000 / $73100`; hover here) | 2 404 |
| `$73C00-$73FFF` | 1 024 | `p3b_*` code + PD | 504 |
| `$74000-$757FF` | 6 144 | `pm_tooltip` (code, state, wording) | 3 971 |
| `$75800-$75BFF` | 1 024 | `tt_ptr`, `pm_mste`, `pm_cachecap`, `pm_intro_*`, `fal_ym` | 670 |
| `$75C00-$763FF` | 2 048 | `p4_*` code + P block | 1 674 |
| `$76400-$767FF` | 1 024 | `snd_*` code + SV | 840 |
| `$76800-$771FF` | 2 560 | `p6_tri`, `p6_cpy` (+ ~100 B slope generator) | 2 038 |
| `$77200-$773FF` | 512 | `p7_*` | 160 |
| `$77400-$77BFF` | 2 048 | `hd_*` code (HD build) | 1 564 |
| `$77C00-$77FFF` | 1 024 | `test_*`, reserve | - |

Used 14.4 KB of 22.5 KB by master's sizes. Tightest: `p6_` (80 %), `hd_` (76 %), `snd_` (82 %), `p4_` (82 %). If a range overflows, take
from the reserve or the tooltip range first; last resort is the HIGH reserve (`$EE400..`), which the cap protects.
Rule for patch authors: **a blob or `; data:` span larger than 2 KB goes HIGH; everything else LOW.**

### 3.2 HIGH area `$B0000-$F6FFF`: big buffers only, same addresses on every machine, floppy and HD

| range | bytes | blob | initialised | used on |
|---|---:|---|---|---|
| `$B0000-$B7CFF` | 32 000 | **C**, third screen (256-aligned; A = `$1D500`, B = `$25200`) | never (overwritten by the 32 000 B window copy each pass) | all, with `p7_*` |
| `$B7D00-$B7FFF` | 768 | guard G1 | pattern in gate builds | - |
| `$B8000-$BBFFF` | 16 384 | **SLOPE** table (`p6_slope`) | generated by an `init` routine (3.5) | all, with `p6_tri` |
| `$BC000-$BFFFF` | 16 384 | **STAGE**, DMA staging buffer (`snd_core`) | zero-fill record | STE-class sound only |
| `$C0000-$C1FFF` | 8 192 | interpolation lists: OLD `$C0000` (2 048), LST `$C0800` (5 120), 1 024 spare | zero-fill | all, with `p3b_*` |
| `$C2000-$C2FFF` | 4 096 | `hd_core` V `$C2000-$C21FF`, private stack below `$C3000` | zero-fill | HD build |
| `$C3000-$DEFFF` | 114 688 | **S**, HD swap buffer, `SMAX = $1C000` | copied from R by `hd_core init` | HD build |
| `$DF000-$EE3FF` | 62 464 | **sprite cache**: HDR `$DF000`, BLT `$DF004`, TAGS `$DF010`, SCR `$DF300`, SLOTS `$DF400` (48 x 1 280) | lazy (magic word, as master) | machines without a blitter (ST, TT, Falcon per master's probe) |
| `$EE400-$F6FFF` | 35 840 | reserve (sprite-cache growth: up to 28 more slots; or unassigned) | pattern in gate builds | - |
| `$F7000-$F7FFF` | 4 096 | **not ours**: start-up stack of `front` / `uinit` on 1 MB machines | - | - |
| `$F8000-$FFFFF` | 32 768 | **not ours**: TOS screen RAM on 1 MB (TOS may print there during an HD call) | - | - |

Sum 290 816 B = `$B0000..$F6FFF` exactly. WW1 differences from master that the port must apply:
* C cannot be `$70000` (inside WW1's FX data / BSS); every `BUFC` reference becomes `$B0000`.
* Sprite sheets are `$320C0..$4475B` (master `$312A0..$3F29C`); SPRITE24 / SPRITE32 hold 43 frames each against master's 27 (20 640 / 480,
  27 520 / 640) and the start view draws 51 sprites per pass against 18 [stage `profile_ww1.md`], so the 48-slot cache may thrash on a plain ST.
  Stage 5 measures the hit rate on ST; the reserve directly above the cache allows 8 sets x 9 ways (+ 30 720 B) without moving anything.
* WW1's people table is `$55DF4..$5A7C7` = 378 records of 50 B [INFERENCE from the neighbouring variable `$5a7ca` in `addrmap.md`; verify
  against the men-update loop bound], so OLD / LST need 1 512 + 3 780 B; master's 512-record sizes are reserved anyway.
* `SMAX`: R must end below the lowest address the game hands to the disk code, which is the save disk's sector 0 block `$1C860`
  (`$1caac lea $1c860(pc),a0 / jsr $ddea`; the other buffers are `$44c3e`, the screens, `$2ee00` and up) [obs: disassembly]. `SMAX = $1C000`
  gives R up to `$1C008`. `hd_core init` must refuse HD mode when `RHI > $1C800` (message and exit, as master does for R > SMAX).

### 3.3 The cache cap
`pm_cachecap`: site `$e3f2` `movea.l $2cfda.l,a1` (6 B, `2279 0002cfda`) -> `jsr hook`; hook (24 B, master's, LOW area):
```
movea.l $2cfda.l,a1 ; move.l a1,d0 ; beq.s ret ; add.l d2,d0 ; cmp.l #CAPLIM,d0 ; bls.s ret ; suba.l a1,a1 ; ret: rts
```
`d2` = unpacked size (set at `$e3d0`), `d0` is reloaded at `$e400`, `a1 = 0` takes the game's own no-cache branch `$e3fe beq $e42a`.
`CAPLIM = $B0000` = `HI_BASE` in `wwpatch.py` (one constant; the build must refuse any HIGH blob below it).

| CAPLIM | what is no longer cached | cost per occurrence (floppy, measured below) | RAM gained for us |
|---|---|---|---|
| **`$B0000` (chosen)** | nothing a game on the EA disk loads (only 12 / 13 / 7, absent from the disk) | **0** | - |
| `$A8000` | the second of LOSE / WIN seen in a session | + 3.3 s per repeated lose or + 2.2-2.4 s per repeated win | 32 KB |
| `$A0000` | LOSE and WIN | + 3.3 s and + 2.2-2.4 s, from the second showing on | 64 KB |
| below `$9FC58` | QAZ / CAPGRAPH / MAP / the 216 B record | + 2.5 s, + 1.9 s, + 5.5 s, + 3.9 s **per land start** | not worth it |

Measured load times, call to return of the loader, emulated [obs, `events.json` of each run]:

| resource | from disk: STE 50 Hz / Mega STE 60 Hz / ST 50 Hz | from the cache |
|---|---|---|
| 14 LOSE | 172 VBL = 3.44 s / 216 = 3.60 s / 176 = 3.52 s | 8-9 VBL = 0.16 s |
| 15 WIN | 117 = 2.34 s / 145 = 2.42 s / 130 = 2.60 s | 8 VBL |
| 1 QAZ, 8 CAPGRAPH | 135, 103 / 170, 147 / 146, 109 VBL | 7-11 VBL |
| 10 MAP, 16 | 292, 194 / 356, 219 / 289, 182 VBL | 16-20, 0-1 VBL |
| 11 MAPDATA (never cached, every land) | 174-197 / 206-217 / 175-187 VBL | - |

**Live prototype of the cap in WW1** [obs, `r4_cap_a0000`]: the 24 bytes poked at `$77F00`, the site rewritten at the option screen,
`CAPLIM = $A0000` to force the skip path: `14` and `15` take `skip` (breakpoint at the `suba`), `a1 = 0` at `$e3f8`, cursor stays `$9FC58`
through lose x2, win x2 and five land starts, both pictures shown and stable (`lose1 still there after 8 s: (0.69, 16 colours)`), the hook
bytes intact at the end, pattern `$A0000-$F7EFF` 0 changed. Repeated lose 173-177 VBL, repeated win 123-127 VBL (from the disk each time).
With `CAPLIM = $B0000` the same hook never skips in these scenarios (cursor maximum `$AF658`, 2 472 B below the limit) [INFERENCE from `r1`].

### 3.4 1 MB against more RAM, floppy against HD, and what degrades
| | floppy | HD |
|---|---|---|
| addresses | section 3.1 / 3.2 | the same; `hd_*` code LOW `$77400`, V + stack `$C2000`, S `$C3000` |
| unused spans | `$C2000-$DEFFF` (118 784 B) stay free | S's unused tail `[$C3000 + RLEN, $DF000)` |
| overlay window / `PMLATE.DAT` | - | **not needed**: WW1 is one program (TOS loads all of `WW1.PRG`; no second stage is read by our loader), and no load destination lies inside R (lowest `$1C860`) [INFERENCE from the buffer list above; `hd_core` asserts it] |
| disk space | 34 816 B free on the stage-2 default floppy [obs `mdir`]; a master-size payload adds about 27 KB of records, of which 16 KB is the slope table | no limit |

| extra | needs | ST 1 MB | STE 1 MB | Mega STE 4 MB | TT / Falcon (4 MB) |
|---|---|---|---|---|---|
| tick, rain, interpolation, keys, tooltips, hover, noprot, credit, cap, intro | RAM only (LOW + 8 KB HIGH) | yes | yes | yes | yes |
| triple buffering | 32 000 B HIGH | yes | yes | yes | yes |
| `p6_*`, pointer patches | 16 KB HIGH | yes | yes | yes | yes |
| sprites (`p4_spr`) | blitter, else 62 KB cache HIGH | cache | blitter | blitter | cache (per master's probe) |
| DMA sound | STE-class DMA hardware + 16 KB HIGH | **original YM sample player** (as master) | yes | yes | yes |
| 16 MHz + cache (`pm_mste`) | Mega STE | - | - | yes | - |
| `tt_ptr`, caches off | TT / Falcon | - | - | - | yes |
| HD | S <= 114 688 B, `RHI <= $1C800` | yes | yes | yes | yes |

**No extra needs more than 1 MB**; the only degradations are hardware ones (no DMA on a plain ST, no blitter), exactly as in master.
A larger machine gets nothing extra and needs nothing different. Less than 1 MB: the payload must not be installed at all (work item 2).
An HD set-up whose R exceeds the limit (many AUTO programs / accessories): HD mode refuses with a message; the floppy build is unaffected.

### 3.5 The slope table on the floppy
Master stores the 16 384 B table in the payload. WW1's floppy has 34 816 B free against about 27 KB still to come. Recommendation:
generate it at boot from an `init` routine (formula in master's `p6_slope.s` header: `dy > mag: (mag << 16) / dy`, else
`((mag << 8) / dy) << 8`, both quotients fit 16 bits; 4 032 `divu`, well under 0.1 s) and keep master's `rept` table as the build-time
oracle: the gate compares `$B8000-$BBFFF` after boot with the assembled table, byte for byte. Floppy cost drops to about 11 KB.

## 4. Proof plan (gates)

All on REAL built disks, cold boot. Machines for every row: **STE 1 MB TOS 1.62, Mega STE 4 MB TOS 2.06 (8 and 16 MHz), ST 1 MB TOS 1.04**;
TT / Falcon 4 MB in the stage-6 matrix. Scenario for every fill gate: boot, option screen, chart, map view, save + load (floppy: blank
save-disk image, stage 2's method; HD: `SAVEDISK.DAT`), Retire lose, new land, Retire win, CONTINUE CONQUEST to a second land (chart click
ST (62,50) once the first island is won), lose again, START NEW CONQUEST (YES), win again, PLAY RANDOM LAND, **one real battle** (stage 5:
the random land starts with an enemy captain next to the player's [obs `r1/random.png`]), 20 min soak.

| gate | what it proves | pass criterion | status |
|---|---|---|---|
| **M0** game alone | the original never writes `$B0000-$F6FFF` | pattern 0 changed at every checkpoint | **done** [obs 2.4] on the three machines, without battle / soak / HD |
| **M1** high fill, every stage-4/5 build | neither the game nor any patch writes outside its declared span | the debugger loads the pattern at the hand-over into every HIGH byte the build's manifest does not list as `used` (guards and reserve always); 0 changed; `used` code / constant spans (LOW `expect.bin`, SLOPE) byte-exact; run-time data spans masked | tool work: item 1 |
| **M2** each blob region before its patch lands | the span is free in the build WITHOUT that patch | M1 of the previous build covers it; listed per patch in its result note | per item |
| **M3a** cap, normal | 0 extra disk reads | loader trace: 14 and 15 `store` once, later calls from the cache (<= 12 VBL), no `skip`, cursor `$AF658` | item 3 |
| **M3b** cap, forced | the skip path is safe | cursor raised by `$10000` at the option screen (debugger write to `$2cfda`): lose ends above `$B0000` -> `skip`, picture stable 8 s, cursor unchanged, pattern + C intact | item 3 |
| **M3c** cap, negative control | the gate can fail | the same raise with the site restored: pattern in `$B0000..` changed -> the gate prints FAIL | item 3 |
| **M4** C and guards with `p7_*` | triple buffering stays inside C | G1 `$B7D00-$B7FFF` pattern intact, `$AF658-$AFFFF` zero, md5 of the cached resources (`$80000..cursor`) equal before / after a session | item 11 |
| **M5** HD | TOS swap stays inside S; nothing else moves | GEMDOS emulation and ACSI + HDDRIVER, STE 1 MB + Mega STE 4 MB: `RLEN` printed, pattern in `[S + RLEN, $DF000)`, reserve, guards: 0 changed after boot, map, save + load, lose, win, battle; V / S / stack masked | item 12 |
| **M6** small RAM | no crash below 1 MB | 512 KB ST / STE: baseline of the original first, then the patched disk behaves the same (unpatched game) | item 2 |
| **M7** floppy capacity | the PRG fits | `wwpatch.py checkdisk`; build error when the records exceed the free clusters | item 1 |

Negative controls belong to M1 too: one build with a test patch that writes a byte into the reserve must FAIL.

## 5. Risks
1. **Cap value drift**: a cap at master's `$B8000` would let a first-time resource be cached into C. Single constant `HI_BASE = CAPLIM`,
   build check, gate M3.
2. **Paths never run**: a real battle, the ending (`$1b3a6`; its files are missing from the disk), `BITMAP.PAK` (`$14994`), custom maps
   (`MAP0000.DAT` string at `$e771`), hours of play. Bounded for the cache by construction once the cap is in; for other writers only by
   the pattern gates (battle and soak are in M1's scenario).
3. **HD on WW1 is unbuilt**: R sizes are master's; the "no overlay" claim rests on the buffer list in 3.2; `SMAX` above master's proven
   `$19000`. Gate M5 on two machines before release; fall back to `SMAX = $19000` if anything in `$19008..$1C008` is handed to GEMDOS.
4. **Sprite cache thrash on ST** (more frames, more trees): a speed risk only; measured in stage 5, room reserved.
5. **LOW area overflow** when the WW1 tooltip wording or key tables grow: 8 KB slack today; fallback rule in 3.1.
6. **`$F7000-$FFFFF`** is free in every floppy run here but is TOS's stack / screen on 1 MB machines: never placed there, never gated as ours.
7. **Warm boots**: HIGH RAM is not zero after a reset; every data span needs its zero-fill record or lazy init (master's rule).
8. **Stage 2's payload gate** compares only `$72000-$77FFF`; the HIGH gates do not exist until item 1 is done.

## 6. Work items for the implementing agents (stage 4, then stage 5), in order

**Stage 4**
1. **`wwpatch.py` / `wwgate.py`: the HIGH area.** `HI_BASE = $B0000`, `HI_END = $F7000`; the LOW / HIGH prefix tables of 3.1 / 3.2 as
   `PREFIX_RANGES`; build errors for a span outside its range, an overlap, a span > 2 KB in LOW; manifest lists `used` and `data` for both
   areas plus `free_hi` spans; `wwgate.py cell --fill-hi` loads the pattern at the hand-over breakpoint (recipe: `/tmp/pmww1mem/memrun.py`,
   `fill_byte`, `b pc = $576 && ($576).w = $41f9 :trace :once :file`), compares at every step, and gains the steps `continue`, `random`,
   `battle`, plus the loader trace (`$e34c`, `$e388`, `$e3f8`, `$e42a`, cap `skip`). Gate: M1 on the current build + the negative control.
2. **`front` guard** (`patches/core.s`): install the payload only when the program's TPA covers `$72000..$F7FFF` (basepage `p_hitpa >= $F8000`
   and `phystop >= $100000`); otherwise jump straight to the original code. Gate M6.
3. **`pm_cachecap`** (unless stage 2 delivered it with `CAPLIM = $B0000`): section 3.3, blob in `$75800-$75BFF`. Gates M3a/b/c + stage 2's
   lose / win / round-3 cell.
4. `pm_mste`, `tt_ptr`, `p4_clamp`, `p4_ptr_a/b` (LOW only). Gates: master's per patch + M1.
5. `p3b_interp` / `p3b_delta` with OLD `$C0000`, LST `$C0800` (zero-fill records); verify the people-record count first; `tick_rain`.
6. `qol_hover*`, `pm_tooltip` (stage 3), `pm_intro_*` if WW1 has the delay loops: LOW only.

**Stage 5**
7. `snd_*`: code LOW `$76400`, STAGE `$BC000`.
8. `p4_spr`: code LOW, cache `$DF000` (sheet range `$320C0..$4475B`); report the cache hit rate on ST in the tree-heavy start view; grow
   into the reserve only with numbers.
9. `p6_slope` (init-generated at `$B8000`, oracle gate), `p6_tri`, `p6_cpy`.
10. Floppy capacity check after 7-9 (M7).
11. `p7_triple_*` with C = `$B0000`; gates M4 + master's trace / pixel / state gates.
12. HD build: `hd_load` (site: by-name loader `$d962`, 4 callers), `hd_sector` (sector driver `$ddea`, 6 FAT + 6 save callers), `hd_kbd`,
    `hd_core` (code `$77400`, V `$C2000`, S `$C3000`, `SMAX $1C000`, `RHI <= $1C800` check, no overlay, no `PMLATE.DAT`), `SAVEDISK.DAT`. Gate M5.
13. **Performance gates: map view, a men-moving scene AND one real battle at 8 and 16 MHz** (sprite-heavy frames; no WW1 battle was
    profiled in `profile_ww1.md`). Route: PLAY RANDOM LAND, save a snapshot with both captains in view, order the attack.
14. Full M1-M7 matrix on the final floppy and HD builds; results into the stage note with the raw `GATE` lines.

## 7. Not done / limits of this note
* No patched WW1 build with HIGH blobs exists; every HIGH placement is a design backed by the game-alone proof (M0) and master's sizes.
* No HD run, no TT / Falcon run, no 512 KB run, no battle, no ending; the Mega STE cell ran at 8 MHz only.
* The cap prototype was a debugger poke at `CAPLIM = $A0000`; `$B0000` itself was not run with the hook installed.
* A byte scan of the image for operands in `$80000-$FFFFF` is useless (757 candidate values, opcode and data words); the argument is the
  loader analysis plus the pattern runs.
* `PLAN.md` 2.1 calls `MAPDATA.DAT` "291 KB": the file is 71 928 B (291 148 B is the whole root directory) [obs `mdir`].

## 8. Evidence (`/tmp/pmww1mem/`, volatile; key lines are quoted above)
`README.txt`, `memrun.py` (driver: pattern load, loader trace, checkpoints, live cap), `r1/` `r2_mste/` `r3_st/` `r4_cap_a0000/`: `run.log`
(checkpoint lines `CP <name>: vbl .. cursor .. cache {..} pattern changed {..}`), `events.json` (loader trace), `dumps/*.bin` (1 MB RAM per
checkpoint), screenshots (`chart_continue.png`, `land3.png` = the second land, `random.png`, `lose*.png`, `win*.png`).
Example raw lines (`r1/run.log`):
```
CP map1: vbl 6320 cursor $9fc58 cache {1:$90258, 8:$97f58, 10:$800d8, 16:$80000} pattern changed {'b0000-f7f00': (0, ''), 'f8000-100000': (0, '')}
CP win1: vbl 19838 cursor $af658 cache {1:$90258, 8:$97f58, 10:$800d8, 14:$9fc58, 15:$a7958, 16:$80000} pattern changed {'b0000-f7f00': (0, ''), 'f8000-100000': (0, '')}
CP random_attack_100s: vbl 48324 cursor $af658 cache {...same...} pattern changed {'b0000-f7f00': (0, ''), 'f8000-100000': (0, '')}
saveload: {'n': 101376, 'd_saved_loaded': 0, 'd_saved_pre': 297, 'disk_eq': True, 'disk_len': 409600, 'slot_flag': 255, 'ticking': True}
```
Master sources read: `work/notes/{retire,release,loading,triple,snd,p4_raster}.md`, `tools/pmpatch.py` (`PREFIX_RANGES`), `patches/*.s` headers,
`build/dist_build/{floppy,hd}.json`.
