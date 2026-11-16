# Moonshine Racers: integration wave (MSRIntegrate): tool safety, road load-time generation, T=30, defaults, gates

Machine for every number: Hatari 2.6.1, STE TOS 1.62 1 MB 8 MHz 50 Hz unless named. Raw outputs are pasted below (they live in `work/int/`). `[INFERENCE]` marks what no tool output here proves.
**Gate-tool bug (reported by MSRHud, fixed by the lead, `tools/msrabtest.py` line ~141):** the `m` count of Hatari's debugger is DECIMAL; the old per-pass STATE recipe wrote it in hex, so `m $29c8 b38` / `m $4500 b00` were rejected and `m $1000 400` dumped only 400 bytes: every earlier msrabtest STATE comparison (mr_*, rd_*, ms_*) only compared `$1000-$118f` and `$dae6`; pixel gates, the offline whole-RAM tests of `rd_*`, and the `work/tick` / `work/extrap` `exp_state*.py` recipes (decimal counts) were unaffected.
The fixed tool compares `$1000-$13ff, $29c8-$34ff, $4500-$4fff, $dae6` (1024 + 2872 + 2816 + 4 = 6,716 bytes per pass); I added a printout of the number of bytes compared. Section 6 re-runs the STATE gate with it on the integrated default set: **0 differing bytes on all four scenes**.

## 0. Result in one page
- Tool: `; ram:` (reserved work RAM, not in the image, collision- and layout-checked, listed by `list`/`doc {RAM}`), `; requires:` / `; conflicts:` (enforced by build/live/`--only`/defaults/verify), undeclared footprint overlaps refused by `verify` (it found a real one: `test_blob36k`'s ramp `$B3100` lies inside `mr_edge`'s blob; now declared). Unchanged default HD and floppy builds are byte-identical before/after the tool change (section 1).
- Road tables are generated at the race setup by the new patch `rd_init` (site `$78f6`), 20 VBL before the race loop starts instead of inside the first road frame; the lazy paths remain; pixel-identical (table md5 equal to the lazily built tables; A/B of the restarted race on tracks 5 and 12 IDENTICAL).
- `TICK equ 30` (10 passes/s): state per pass identical to stock (0 differing bytes over 164 / 230 common passes, time-out and restart included); 10.000 passes/s at 8/16/32 MHz and at 50/60 Hz; the worst driving pass at 8 MHz with everything on is 4.96 VBL of 5.00 (race_start), grid 3.96, up 4.32; two post-restart passes overrun (4.96/5.14 VBL).
- Defaults: `rd_geom rd_draw rd_init` are `default: yes` (dependencies encoded); `mx_*`, `ms_*`, `test_*`, `mr_negctl` stay `default: no`. `tools/play.sh`: `--road` is a no-op alias, `--extrap` swaps `mt_sync` for `mx_sync` through the declared conflict.
- Unproven / for the lead: see the last section.

## 1. Tool safety (task 1)
Tool changes (`tools/msrpatch.py`): header lines `; ram: $lo-$hi [label]`, `; requires: ...`, `; conflicts: ...`; `footprint()` / `check_pairs()` (every pair of patches: site, blobs, `; data:`, `; ram:` must not overlap unless a conflict is declared; every `; ram:` must be inside the free run of each layout and ZERO in the six stock RAM dumps), `check_selection()` (`build`, `live`, `--only`, the default sets, `verify`), `build_layouts()` (1 MB: `$B2800-$E83FF`; 4 MB only with the file patch `pp_bigram_cache` or in the floppy build: without it the whole-image disk cache overwrites the payload area, delivery.md section 5; a HD `build` with a `; ram:` patch and no `pp_bigram_cache` is refused, `live` (a 1 MB snapshot) is not), `list` prints the reservation and the dependency table and the payload/RAM map, `doc` expands `{RAM}`.
Declared rules (from the notes and the code): `mt_sync requires mt_clock mt_pre` (without the clock PEND never clears: the pacer sleeps forever) and `conflicts mx_sync`; `mt_pre requires mt_clock`; `mx_sync requires mt_clock mt_pre mx_pre`, `conflicts mt_sync`; `mx_pre requires mx_sync mt_clock mt_pre`; `rd_init requires rd_geom rd_draw`; `rd_geom` and `rd_draw` are independent (each gated alone, `road.md` 6.3); `test_marker`/`test_blob36k` conflict (same site), `test_blob36k` conflicts `mr_edge` (blob overlap).
(c) Unchanged default builds, md5 of every output file before (`work/int/base_*.md5`, tool and patches as shipped by the earlier waves) and after the tool change (`new_*.md5`; `rd_*` still `default: no`, `TICK 36`):
```
$ diff work/int/base_hd.md5 work/int/new_hd.md5        -> (no output)  HD IDENTICAL
$ diff work/int/base_floppy.md5 work/int/new_floppy.md5 -> (no output)  FLOPPY IDENTICAL
(build with rd_geom rd_draw explicitly: RUNME.TOS differs, expected: the two patches gained a pre-warm entry in this wave)
```
Positive and negative builds (raw, `work/int/tool_gates.txt`):
```
== (b) dependencies/conflicts

$ python3 tools/msrpatch.py build --only mt_sync --out build/int_neg
invalid patch selection:
  mt_sync requires mt_clock, which is not in this build (add it to --only)
  mt_sync requires mt_pre, which is not in this build (add it to --only)
[exit 1]

$ python3 tools/msrpatch.py build --only pp_bigram_cache mt_clock mt_pre mt_sync mx_pre mx_sync --out build/int_neg
invalid patch selection:
  mt_sync conflicts with mx_sync: they must not be built together
  mx_sync conflicts with mt_sync: they must not be built together
[exit 1]

$ python3 tools/msrpatch.py build --only mx_sync mt_clock mt_pre --out build/int_neg
invalid patch selection:
  mt_pre requires mt_sync, which is not in this build (add it to --only)
  mx_sync requires mx_pre, which is not in this build (add it to --only)
[exit 1]

$ python3 tools/msrpatch.py live --only mt_sync mt_pre --out build/live/int_neg
invalid patch selection:
  mt_pre requires mt_clock, which is not in this build (add it to --only)
  mt_sync requires mt_clock, which is not in this build (add it to --only)
[exit 1]

$ python3 tools/msrpatch.py build --only test_marker test_blob36k --out build/int_neg
invalid patch selection:
  test_blob36k conflicts with test_marker: they must not be built together
  test_marker conflicts with test_blob36k: they must not be built together
[exit 1]

$ python3 tools/msrpatch.py build --only rd_init rd_geom --out build/int_neg
invalid patch selection:
  rd_init requires rd_draw, which is not in this build (add it to --only)
[exit 1]
-- positive

$ python3 tools/msrpatch.py build --only pp_bigram_cache mt_clock mt_pre mx_pre mx_sync --out build/int_pos_mx
invalid patch selection:
  mt_pre requires mt_sync, which is not in this build (add it to --only)
[exit 1]

$ python3 tools/msrpatch.py build --only pp_bigram_cache mt_clock mt_pre mt_sync --out build/int_pos_mt
$0d128     6 52390000611b -> 4eb9000b8000   [mt_clock]
$07b0a     6 4eb900017c42 -> 4eb9000b8200   [mt_pre]
$07b74     6 4eb90000d1e4 -> 4eb9000b8100   [mt_sync]
[exit 0]

$ python3 tools/msrpatch.py build --only pp_bigram_cache rd_geom rd_draw rd_init --out build/int_pos_rd
$17c42     8 22784b8445f84ff8 -> 4ef9000b50044e71   [rd_draw]
$100b4     8 41f8456443f81bbc -> 4ef9000b40044e71   [rd_geom]
$078f6     6 4eb90000fde0 -> 4eb9000b6000   [rd_init]
[exit 0]
-- positive (after mt_pre fix)

$ python3 tools/msrpatch.py build --only pp_bigram_cache mt_clock mt_pre mx_pre mx_sync --out build/int_pos_mx
$07b0a     6 4eb900017c42 -> 4eb9000b8200   [mt_pre]
$07b46     6 4eb90000e406 -> 4eb9000b8300   [mx_pre]
$07b74     6 4eb90000d1e4 -> 4eb9000b8100   [mx_sync]
[exit 0]

== (a) reserved RAM (temporary patch patches/zz_ramtest.s: site $78ba, identity bytes, one `; ram:` line; deleted afterwards)
-- ram $E0000-$E0FFF inside rd_draw's reservation

$ python3 tools/msrpatch.py build --only pp_bigram_cache rd_draw zz_ramtest --out build/int_neg
    ram of the orig floppy: 22784b8445f84ff8  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 4eb90000d140  (match)   [work/floppy/ram_answered.bin]
    rd_draw ram rd_draw window tables (2 x 24 KB), colour table copy, table pointer WPTR $db000-$e7fff overlaps zz_ramtest ram test $e0000-$e0fff (no `; conflicts:` declared)
verify: 1 FAILED
build aborted: a site's orig does not match the game
[exit 1]

$ python3 tools/msrpatch.py verify
    ram of the orig floppy: 5347284b1219  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 49f90001058a  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 044000065347  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 2204  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 52390000611b  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 4eb900017c42  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 4eb90000d1e4  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 4eb90000e406  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 4eb90000d1e4  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 22784b8445f84ff8  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 41f8456443f81bbc  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 4eb90000fde0  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 41f900070000  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 2038100822381004  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 41f900070000  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 4eb90000d140  (match)   [work/floppy/ram_answered.bin]
    rd_draw ram rd_draw window tables (2 x 24 KB), colour table copy, table pointer WPTR $db000-$e7fff overlaps zz_ramtest ram test $e0000-$e0fff (no `; conflicts:` declared)
    dependencies/conflicts/reserved RAM: FAILED
verify: 1 FAILED
[exit 1]
-- ram $B8F00-$B8F0F inside mt_clock's data

$ python3 tools/msrpatch.py build --only pp_bigram_cache mt_clock zz_ramtest --out build/int_neg
    ram of the orig floppy: 52390000611b  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 4eb90000d140  (match)   [work/floppy/ram_answered.bin]
    mt_clock data $b8f00-$b8f03 overlaps zz_ramtest ram test $b8f00-$b8f0f (no `; conflicts:` declared)
    mt_clock data $b8f08-$b8f0b overlaps zz_ramtest ram test $b8f00-$b8f0f (no `; conflicts:` declared)
verify: 2 FAILED
build aborted: a site's orig does not match the game
[exit 1]
-- ram $E8000-$E9FFF beyond the free run (ends $E83FF)

$ python3 tools/msrpatch.py build --only pp_bigram_cache zz_ramtest --out build/int_neg
    ram of the orig floppy: 4eb90000d140  (match)   [work/floppy/ram_answered.bin]
    zz_ramtest ram test $e8000-$e9fff is not free in the 1MB layout
    zz_ramtest ram test $e8000-$e9fff is not free in the 4MB layout
    zz_ramtest ram test $e8000-$e9fff is not zero in the stock game's RAM dump ram_hook_1024.bin
    zz_ramtest ram test $e8000-$e9fff is not zero in the stock game's RAM dump ram_entry_1024.bin
    zz_ramtest ram test $e8000-$e9fff is not zero in the stock game's RAM dump ram_race0.bin
    zz_ramtest ram test $e8000-$e9fff is not zero in the stock game's RAM dump ram_race_start.bin
    zz_ramtest ram test $e8000-$e9fff is not zero in the stock game's RAM dump ram_race_grid.bin
    zz_ramtest ram test $e8000-$e9fff is not zero in the stock game's RAM dump ram_race_up.bin
verify: 8 FAILED
build aborted: a site's orig does not match the game
[exit 1]

$ python3 tools/msrpatch.py verify
    ram of the orig floppy: 5347284b1219  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 49f90001058a  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 044000065347  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 2204  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 52390000611b  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 4eb900017c42  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 4eb90000d1e4  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 4eb90000e406  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 4eb90000d1e4  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 22784b8445f84ff8  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 41f8456443f81bbc  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 4eb90000fde0  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 41f900070000  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 2038100822381004  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 41f900070000  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 4eb90000d140  (match)   [work/floppy/ram_answered.bin]
    zz_ramtest ram test $e8000-$e9fff is not free in the 1MB layout
    zz_ramtest ram test $e8000-$e9fff is not free in the 4MB layout
    zz_ramtest ram test $e8000-$e9fff is not zero in the stock game's RAM dump ram_hook_1024.bin
    zz_ramtest ram test $e8000-$e9fff is not zero in the stock game's RAM dump ram_entry_1024.bin
    zz_ramtest ram test $e8000-$e9fff is not zero in the stock game's RAM dump ram_race0.bin
    zz_ramtest ram test $e8000-$e9fff is not zero in the stock game's RAM dump ram_race_start.bin
    zz_ramtest ram test $e8000-$e9fff is not zero in the stock game's RAM dump ram_race_grid.bin
    zz_ramtest ram test $e8000-$e9fff is not zero in the stock game's RAM dump ram_race_up.bin
    dependencies/conflicts/reserved RAM: FAILED
verify: 8 FAILED
[exit 1]
-- ram $B7000-$B70FF on the site table

$ python3 tools/msrpatch.py build --only pp_bigram_cache zz_ramtest --out build/int_neg
    ram of the orig floppy: 4eb90000d140  (match)   [work/floppy/ram_answered.bin]
verify: ALL OK
image overlap: site table $b7000-$b701f vs zz_ramtest ram (test) $b7000-$b70ff
[exit 1]
-- ram $C0000-$C0FFF free and unowned: HD+pp_bigram_cache accepted, HD without it refused (4 MB layout), live accepted (1 MB snapshot), floppy accepted

$ python3 tools/msrpatch.py build --only pp_bigram_cache zz_ramtest --out build/int_neg
    ram of the orig floppy: 4eb90000d140  (match)   [work/floppy/ram_answered.bin]
verify: ALL OK
built /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/int_neg with 1 patch(es) + 1 file patch(es); payload 22784 B at $b2700-$b7fff
[exit 0]

$ python3 tools/msrpatch.py build --only zz_ramtest --out build/int_neg
    ram of the orig floppy: 4eb90000d140  (match)   [work/floppy/ram_answered.bin]
verify: ALL OK
reserved RAM (`; ram:`) of zz_ramtest is free at 1 MB only: a HD build needs the file patch pp_bigram_cache for the 4 MB layout (whole-image disk cache over $B2700.., delivery.md section 5)
[exit 1]

$ python3 tools/msrpatch.py live --only zz_ramtest --out build/live/int_neg
    ram of the orig floppy: 4eb90000d140  (match)   [work/floppy/ram_answered.bin]
verify: ALL OK
wrote /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/live/int_neg.img and /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/live/int_neg.json (1 sites)
[exit 0]

$ python3 tools/msrpatch.py build --floppy --only zz_ramtest --out build/int_neg_floppy
    ram of the orig floppy: 4eb90000d140  (match)   [work/floppy/ram_answered.bin]
verify: ALL OK
floppy: disk A 819200 B, disk B 819200 B; payload 544 B (2 sectors) at t0.0s2x2
[exit 0]
-- list line:
zz_ramtest         no       $078ba     6 - / - / ram $c0000-$c0fff (test)
-- ram in a non-zero part of the stock game RAM ($7000-$7FFF) is refused by verify:

$ python3 tools/msrpatch.py verify
    ram of the orig floppy: 5347284b1219  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 49f90001058a  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 044000065347  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 2204  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 52390000611b  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 4eb900017c42  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 4eb90000d1e4  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 4eb90000e406  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 4eb90000d1e4  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 22784b8445f84ff8  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 41f8456443f81bbc  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 4eb90000fde0  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 41f900070000  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 2038100822381004  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 41f900070000  (match)   [work/floppy/ram_answered.bin]
    ram of the orig floppy: 4eb90000d140  (match)   [work/floppy/ram_answered.bin]
    mt_pre site $7b0a-$7b0f overlaps zz_ramtest ram test $7000-$7fff (no `; conflicts:` declared)
    mt_sync site $7b74-$7b79 overlaps zz_ramtest ram test $7000-$7fff (no `; conflicts:` declared)
    mx_pre site $7b46-$7b4b overlaps zz_ramtest ram test $7000-$7fff (no `; conflicts:` declared)
    mx_sync site $7b74-$7b79 overlaps zz_ramtest ram test $7000-$7fff (no `; conflicts:` declared)
    rd_init site $78f6-$78fb overlaps zz_ramtest ram test $7000-$7fff (no `; conflicts:` declared)
    zz_ramtest ram test $7000-$7fff is not free in the 1MB layout
    zz_ramtest ram test $7000-$7fff is not free in the 4MB layout
    zz_ramtest ram test $7000-$7fff is not zero in the stock game's RAM dump ram_hook_1024.bin
    zz_ramtest ram test $7000-$7fff is not zero in the stock game's RAM dump ram_entry_1024.bin
    zz_ramtest ram test $7000-$7fff is not zero in the stock game's RAM dump ram_race0.bin
    zz_ramtest ram test $7000-$7fff is not zero in the stock game's RAM dump ram_race_start.bin
    zz_ramtest ram test $7000-$7fff is not zero in the stock game's RAM dump ram_race_grid.bin
    zz_ramtest ram test $7000-$7fff is not zero in the stock game's RAM dump ram_race_up.bin
    dependencies/conflicts/reserved RAM: FAILED
verify: 13 FAILED
[exit 1]
```


## 2. Road load-time generation (task 2)
**Where:** `rd_init`, site `$78f6` = `jsr $fde0.l` in the game's race setup (`$7860-$792c`, disassembly `m68dis.py work/dumps/ram_hook_1024.bin 78cc`): `$7890` sets `$135a` from the list `$1362` indexed by `$102c`; `$78d2-$78f0` build `$164c4 $164ea $163ba $16524 $16404 $16428` = the static tables `$4644 $4ff8 $4154 $3d54 $4564 $68000`; `$78f6` is the first instruction after all of them and before the race loop `$7a88`. The blob replays the `jsr $fde0` and calls the pre-warm entries `$B4000` (rd_geom: `gen_static` + `gen_pt`, 0.9 M cycles) and `$B5000` (rd_draw: `gen_win`, 2.0 M cycles), which run exactly the generators the first road frame would run (each is a no-op when its key (`RDG1`/`PM`, `WPTR`) already matches); the lazy paths stay as the fallback. The pacer never sees it: `mt_sync` runs only in the race pass (`$7b74`).
Raw (cold boot, STE 1 MB, `work/int/init_probe.py`; breakpoints with `e VBL`; build before the T=30 switch, the pacing shown is 6 VBL): rd_init at VBL 6128, `gen_static` 6129, `gen_pt` 6129 (about 6 VBL), `gen_win` 6135 (about 13 VBL), rd_init returns 6148, FIRST race-loop pass `$7a88` at 6151; no generator hit after that:
```
in_race True vbl 5808
after SPACE vbl 6287 $100e 23
> b pc = $b6000 :trace :file /tmp/strun-6dg6sc_q/vbl.txt
pc = $b6000
> b pc = $78fc :trace :file /tmp/strun-6dg6sc_q/vbl.txt
pc = $78fc
> b pc = $b43cc :trace :file /tmp/strun-6dg6sc_q/vbl.txt
pc = $b43cc
> b pc = $b4424 :trace :file /tmp/strun-6dg6sc_q/vbl.txt
pc = $b4424
> b pc = $b567e :trace :file /tmp/strun-6dg6sc_q/vbl.txt
pc = $b567e
> b pc = $7a88 :trace :file /tmp/strun-6dg6sc_q/vbl.txt
pc = $7a88
= %100101101 (bin), #301 (dec), $12d (hex)
= %1001011010 (bin), #602 (dec), $25a (hex)
= %1110000110 (bin), #902 (dec), $386 (hex)
= %10010110010 (bin), #1202 (dec), $4b2 (hex)
= %10111011111 (bin), #1503 (dec), $5df (hex)
= %11100001011 (bin), #1803 (dec), $70b (hex)
= %100000110111 (bin), #2103 (dec), $837 (hex)
= %100101100100 (bin), #2404 (dec), $964 (hex)
= %101010010000 (bin), #2704 (dec), $a90 (hex)
= %101110111100 (bin), #3004 (dec), $bbc (hex)
= %110011101001 (bin), #3305 (dec), $ce9 (hex)
= %111000010101 (bin), #3605 (dec), $e15 (hex)
= %111101000001 (bin), #3905 (dec), $f41 (hex)
= %1000001101110 (bin), #4206 (dec), $106e (hex)
= %1000110011010 (bin), #4506 (dec), $119a (hex)
= %1001011000111 (bin), #4807 (dec), $12c7 (hex)
= %1001111110011 (bin), #5107 (dec), $13f3 (hex)
= %1010100011111 (bin), #5407 (dec), $151f (hex)
= %1011001001100 (bin), #5708 (dec), $164c (hex)
= %1011010110000 (bin), #5808 (dec), $16b0 (hex)
pc = $b6000 :trace :file /tmp/strun-6dg6sc_q/vbl.txt
= %1011111110000 (bin), #6128 (dec), $17f0 (hex)
pc = $b43cc :trace :file /tmp/strun-6dg6sc_q/vbl.txt
= %1011111110001 (bin), #6129 (dec), $17f1 (hex)
pc = $b4424 :trace :file /tmp/strun-6dg6sc_q/vbl.txt
= %1011111110001 (bin), #6129 (dec), $17f1 (hex)
pc = $b567e :trace :file /tmp/strun-6dg6sc_q/vbl.txt
= %1011111110111 (bin), #6135 (dec), $17f7 (hex)
pc = $78fc :trace :file /tmp/strun-6dg6sc_q/vbl.txt
= %1100000000100 (bin), #6148 (dec), $1804 (hex)
pc = $7a88 :trace :file /tmp/strun-6dg6sc_q/vbl.txt
= %1100000000111 (bin), #6151 (dec), $1807 (hex)
pc = $7a88 :trace :file /tmp/strun-6dg6sc_q/vbl.txt
= %1100000001011 (bin), #6155 (dec), $180b (hex)
pc = $7a88 :trace :file /tmp/strun-6dg6sc_q/vbl.txt
= %1100000010001 (bin), #6161 (dec), $1811 (hex)
pc = $7a88 :trace :file /tmp/strun-6dg6sc_q/vbl.txt
= %1100000010111 (bin), #6167 (dec), $1817 (hex)
pc = $7a88 :trace :file /tmp/strun-6dg6sc_q/vbl.txt
= %1100000011101 (bin), #6173 (dec), $181d (hex)
pc = $7a88 :trace :file /tmp/strun-6dg6sc_q/vbl.txt
= %1100000100011 (bin), #6179 (dec), $1823 (hex)
pc = $7a88 :trace :file /tmp/strun-6dg6sc_q/vbl.txt
= %1100000101001 (bin), #6185 (dec), $1829 (hex)
pc = $7a88 :trace :file /tmp/strun-6dg6sc_q/vbl.txt
= %1100000101111 (bin), #6191 (dec), $182f (hex)
pc = $7a88 :trace :file /tmp/strun-6dg6sc_q/vbl.txt
= %1100000110101 (bin), #6197 (dec), $1835 (hex)
pc = $7a88 :trace :file /tmp/strun-6dg6sc_q/vbl.txt
= %1100000111011 (bin), #6203 (dec), $183b (hex)
pc = $7a88 :trace :file /tmp/strun-6dg6sc_q/vbl.txt
= %1100001000001 (bin), #6209 (dec), $1841 (hex)
pc = $7a88 :trace :file /tmp/strun-6dg6sc_q/vbl.txt
= %1100001000111 (bin), #6215 (dec), $1847 (hex)
pc = $7a88 :trace :file /tmp/strun-6dg6sc_q/vbl.txt
= %1100001001101 (bin), #6221 (dec), $184d (hex)
pc = $7a88 :trace :file /tmp/strun-6dg6sc_q/vbl.txt
= %1100001010011 (bin), #6227 (dec), $1853 (hex)
pc = $7a88 :trace :file /tmp/strun-6dg6sc_q/vbl.txt
= %1100001011001 (bin), #6233 (dec), $1859 (hex)
pc = $7a88 :trace :file /tmp/strun-6dg6sc_q/vbl.txt
= %1100001011111 (bin), #6239 (dec), $185f (hex)
pc = $7a88 :trace :file /tmp/strun-6dg6sc_q/vbl.txt
= %1100001100101 (bin), #6245 (dec), $1865 (hex)
= %1100001101000 (bin), #6248 (dec), $1868 (hex)
pc = $7a88 :trace :file /tmp/strun-6dg6sc_q/vbl.txt
= %1100001101011 (bin), #6251 (dec), $186b (hex)
pc = $7a88 :trace :file /tmp/strun-6dg6sc_q/vbl.txt
magic $d0000: Changed back to '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers' dir. | WPTR $e7040: Changed back to '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers' dir. | PM $d0004: Changed back to '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers' dir. | marker: Changed back to '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers' dir.
```
Equality of the tables built at load time vs by the first road frame (two cold boots, memory dump 1 MB, same instant; `work/int/tab_probe.py`; the second build has no `rd_init`):
```
in_race True vbl 5808
$100e 0 vbl 6119
dump 1048576
RDG1 magic: b'RDG1' PM 655360 WPTR 0x102ba $135a 0x102ba $1316 0009
rd_geom ram $D0000-$DAFFF    md5 105083cab5445e5bd5fc73dde4041454
rd_draw ram $DB000-$E7FFF    md5 b6eb3181abd0ae6eb4a15b752294b065
$4154-$4724                  md5 09ccd4ccac7395247b2fba373a431f95
$4ff8-$5bf7                  md5 97d83830ee635afd820277915ac91b13
marker b'MSPO'
in_race True vbl 5809
$100e 0 vbl 6119
dump 1048576
RDG1 magic: b'RDG1' PM 655360 WPTR 0x102ba $135a 0x102ba $1316 0009
rd_geom ram $D0000-$DAFFF    md5 105083cab5445e5bd5fc73dde4041454
rd_draw ram $DB000-$E7FFF    md5 b6eb3181abd0ae6eb4a15b752294b065
$4154-$4724                  md5 09ccd4ccac7395247b2fba373a431f95
$4ff8-$5bf7                  md5 97d83830ee635afd820277915ac91b13
marker b'MSPO'
```

**Static-table assumption, re-verified.** (1) Static analysis: the generators `$163ba $16404 $16428 $164c4 $164ea $16524` contain no reference to `$102c` (`m68dis.py --xref 102c` lists no address in `$163ba-$16560`) and read only constants; the 15 colour tables `$102ba-$1058a` are identical in the hook dump and the race dumps (0 differing bytes in all four race dumps, checked offline). (2) Other tracks: the game offers 15 levels (`$102c`, `$1362` pointer list `$102ba, $102ea, ... $1055a`); I cannot play to track 2 in reasonable time, but the time-out restart replays `$102c & $f` (`$7306-$7318`), so a snapshot of the first race with `$102c` poked to 5, 12 or 14 restarts the race on that track (the game's own setup, `$135a` = the track's table `$103aa / $104fa / $1055a`). Probe (`work/int/level_probe.py`, summary `level_probe_summary.txt`, raw `level_probe_{5,12,14}.txt`; one Hatari run each):
```
level 5:  $135a = $10000 @VBL 15417; $135a = $102ba @VBL 15417; $135a = $103aa @VBL 15551; rd_init @VBL 15642; gen_win @VBL 15643; rd_init returns @VBL 15656; $135a = $10000 @VBL 22488; $135a = $103aa @VBL 22488; $135a = $10000 @VBL 22501; $135a = $103aa @VBL 22501; rd_init @VBL 22726; rd_init returns @VBL 22727
level 12:  $135a = $10000 @VBL 15417; $135a = $102ba @VBL 15417; $135a = $10000 @VBL 15562; $135a = $102ba @VBL 15562; $135a = $104fa @VBL 15596; rd_init @VBL 15687; gen_win @VBL 15688; rd_init returns @VBL 15701; $135a = $10000 @VBL 22936; $135a = $104fa @VBL 22936; $135a = $10000 @VBL 22949; $135a = $104fa @VBL 22949; $135a = $10000 @VBL 23094; $135a = $104fa @VBL 23094; rd_init @VBL 23219; rd_init returns @VBL 23220
level 14:  $135a = $10000 @VBL 15417; $135a = $102ba @VBL 15417; $135a = $10000 @VBL 15562; $135a = $102ba @VBL 15562; $135a = $1055a @VBL 15596; rd_init @VBL 15687; gen_win @VBL 15688; rd_init returns @VBL 15701; $135a = $10000 @VBL 21966; $135a = $1055a @VBL 21966; $135a = $10000 @VBL 21979; $135a = $1055a @VBL 21979; $135a = $10000 @VBL 22124; $135a = $1055a @VBL 22124; rd_init @VBL 22249; rd_init returns @VBL 22250
```
`rd_init` with the new `$135a` runs `gen_win` (13 VBL, once per colour table); `gen_static` / `gen_pt` do not run at all after the first build (the static tables and `$1316` do not change); a second restart with the same track costs 1 VBL (cache hit). The tracks really differ (screens of the patched run at flip 200 after the restart: `work/int/level5_flip200_b78000.png`, `level12_flip200_b78000.png`: different scenery, road and car colours) and the patched pictures equal stock (`msrabtest --poke 102c=...`, 2 flips each):
```
patch set: mr_edge mr_map mr_digit rd_geom rd_draw rd_init  pokes 102c=0005  (live image poke_p_edge+map+digit+rd_geom+rd_draw69495c.img, 22784 B)
PIXELS race_drive  at VBL 15300 flip 120: IDENTICAL  md5 ce611b68 ed3bdfff (stock ce611b68 ed3bdfff)
PIXELS race_drive  at VBL 15300 flip 200: IDENTICAL  md5 719bc02f 59f7e144 (stock 719bc02f 59f7e144)
RESULT: ALL IDENTICAL
patch set: mr_edge mr_map mr_digit rd_geom rd_draw rd_init  pokes 102c=000c  (live image poke_p_edge+map+digit+rd_geom+rd_draw689d6a.img, 22784 B)
PIXELS race_drive  at VBL 15300 flip 120: IDENTICAL  md5 64e7fc26 64e7fc26 (stock 64e7fc26 64e7fc26)
PIXELS race_drive  at VBL 15300 flip 200: IDENTICAL  md5 e365faed c8292df9 (stock e365faed c8292df9)
RESULT: ALL IDENTICAL
```

**Regeneration trigger.** `$135a` has one writer in the game, `$7890` (xref: `$7890`, reader `$17c50`), plus the clears of the `$1300` block at the start of each setup (probe: `$135a` goes `$102ba -> 0 -> $10000 -> $102ba -> track table` within 4 VBL at every setup, and the whole setup repeats several times per restart with the same final value). `$1316` is cleared to 0 and set to 9 in the same block each setup (probe: `$1316 = $0`, then `= $9` at the same VBL on every track, never another value); no code writes it later (xref: only reads at `$e35e $10242 $111f6`). So `gen_pt` runs once (PM = 10) and `gen_win` once per distinct colour table. A road frame between the clear and the set would run the stock path (`$135a = 0` -> `rd_stock0`) or an extra `gen_pt` (`$1316 = 0`); no road frame runs in the setup. Not reached: the real level-2 data of a won race (only the poked track replay); the pictures of tracks beyond 5, 12 and 14 [INFERENCE: same code, same generators].


## 3. Kernel-table caveat of the extra-frame prototype (task 3)
Documented in `work/notes/extrap.md` section 6: the 100 `KTAB` longs come from one race on one track. With the poke method above a second track IS reachable; I did not run the `mx_*` gates on it (not required, mx not shipped): `[INFERENCE]` only.


## 4. T=30 (task 4)
`patches/mt_sync.s`: `TICK equ 30` (MAXLAG = 60). Per-pass state, stock vs integrated default set with tick patches ON (`work/int/exp_state_int.py` = the `work/tick` recipe with the integrated patch list and the full ranges `$1000-$13ff, $29c8-$34ff, $4500-$4fff, $dae6`; `cmpstate.py`, no exclusions). Window 170 / 230 passes (stock `A`, patched `T`, 8 MHz):
```
A ste1m_race_start.sav 8 hits 170 mem bytes/hit 6716
T ste1m_race_start.sav 8 hits 173 mem bytes/hit 6716
st_start_A.json: 170 passes, keys 89..258
st_start_T.json: 173 passes, keys 95..267
common passes 164; differing bytes (excluding $12fe-$1305): 0
A ste1m_race_drive.sav 8 hits 237 mem bytes/hit 6716
T ste1m_race_drive.sav 8 hits 239 mem bytes/hit 6716
st_drive_A.json: 237 passes, keys 0..1706
st_drive_T.json: 239 passes, keys 0..1706
common passes 230; differing bytes (excluding $12fe-$1305): 0
```
The same by `msrabtest.py --flips --state 230` (race_start, race_drive):
```
patch set: mr_edge mr_map mr_digit rd_geom rd_draw rd_init mt_clock mt_sync mt_pre  (live image 8a491982b0.img, 26636 B)
STATE  race_start : stock 238 passes, patched 233, common 233; 1564828 bytes compared (6716 per pass); differing bytes 0 at 0 addresses
STATE  race_drive : stock 231 passes, patched 237, common 228; 1531248 bytes compared (6716 per pass); differing bytes 0 at 0 addresses
RESULT: ALL IDENTICAL
```
(race_drive keys 0..1706 with `$1226` = 5 (time-out) and the key reset 1706 -> 0 (restart) in both runs: the time-out/restart is inside the compared window.)
Speed (`work/int/exp_tick_int.py`, 600 VBL, CPU halted at both ends; `A` = stock, `T` = integrated default, TICK 30; 60 Hz rows: `$ff820a` = `$fc`, rates per 60 Hz second):
```
A ste1m_race_start  8 MHz: vbls 600 pass/s 8.333 VBL/pass 6.000 pos/s 83.33 sw/s 1.333
T ste1m_race_start  8 MHz: vbls 600 pass/s 10.000 VBL/pass 5.000 pos/s 100.00 sw/s 1.583
A ste1m_race_start 16 MHz: vbls 600 pass/s 16.667 VBL/pass 3.000 pos/s 166.67 sw/s 2.583
T ste1m_race_start 16 MHz: vbls 600 pass/s 10.000 VBL/pass 5.000 pos/s 100.00 sw/s 1.583
A ste1m_race_start 32 MHz: vbls 600 pass/s 16.667 VBL/pass 3.000 pos/s 166.67 sw/s 2.583
T ste1m_race_start 32 MHz: vbls 600 pass/s 10.000 VBL/pass 5.000 pos/s 100.00 sw/s 1.500
A ste1m_race_grid   8 MHz: vbls 600 pass/s 9.833 VBL/pass 5.085 pos/s 0.00 sw/s 0.000
T ste1m_race_grid   8 MHz: vbls 600 pass/s 10.000 VBL/pass 5.000 pos/s 0.00 sw/s 0.000
A ste1m_race_grid  16 MHz: vbls 600 pass/s 16.667 VBL/pass 3.000 pos/s 0.00 sw/s 0.000
T ste1m_race_grid  16 MHz: vbls 600 pass/s 10.000 VBL/pass 5.000 pos/s 0.00 sw/s 0.000
A ste1m_race_grid  32 MHz: vbls 600 pass/s 16.667 VBL/pass 3.000 pos/s 0.00 sw/s 0.000
T ste1m_race_grid  32 MHz: vbls 600 pass/s 10.000 VBL/pass 5.000 pos/s 0.00 sw/s 0.000
A ste1m_race_start  8 MHz 60Hz: vbls 600 pass/s 8.500 VBL/pass 7.059 pos/s 85.00 sw/s 1.300
T ste1m_race_start  8 MHz 60Hz: vbls 600 pass/s 10.000 VBL/pass 6.000 pos/s 100.00 sw/s 1.600
A ste1m_race_start 32 MHz 60Hz: vbls 600 pass/s 20.000 VBL/pass 3.000 pos/s 198.30 sw/s 3.100
T ste1m_race_start 32 MHz 60Hz: vbls 600 pass/s 10.000 VBL/pass 6.000 pos/s 100.00 sw/s 1.500
A ste1m_race_grid   8 MHz 60Hz: vbls 600 pass/s 9.700 VBL/pass 6.186 pos/s 0.00 sw/s 0.000
T ste1m_race_grid   8 MHz 60Hz: vbls 600 pass/s 10.000 VBL/pass 6.000 pos/s 0.00 sw/s 0.000
A ste1m_race_grid  32 MHz 60Hz: vbls 600 pass/s 20.000 VBL/pass 3.000 pos/s 0.00 sw/s 0.000
T ste1m_race_grid  32 MHz 60Hz: vbls 600 pass/s 10.000 VBL/pass 6.000 pos/s 0.00 sw/s 0.000
```
`sw/s` is the race clock's high word per second: stock 1.333 at 8 MHz, T 1.583 = x1.19 (a long advancing by a constant step per pass, read through a quantised window: the pass rate 10.000 / 8.333 = x1.2 is exact; the earlier tick gate showed the same quantisation).
**Work per pass vs the tick (task 4 report).** `work/render/work_live.py` (patched live at `$7a88`, pass work = `$d1ca` entry minus loop top `$796a`; the pacer's sleep is after the flip, so it is not in the number), 8 MHz, all default patches on (`mr_* rd_* mt_*`); tick = 5 VBL = 801,280 cycles:
```
race_grid mr_edge+mr_map+mr_digit+rd_geom+rd_draw+rd_init+mt_clock+mt_sync+mt_pre: 160 passes, wrap violations 0; work/pass mean 585,797 cycles = 3.655 VBL, min 558,508 max 635,196; period mean 5.000 VBL
race_start mr_edge+mr_map+mr_digit+rd_geom+rd_draw+rd_init+mt_clock+mt_sync+mt_pre: 169 passes, wrap violations 0; work/pass mean 696,689 cycles = 4.347 VBL, min 632,060 max 794,336; period mean 5.000 VBL
race_up mr_edge+mr_map+mr_digit+rd_geom+rd_draw+rd_init+mt_clock+mt_sync+mt_pre: 169 passes, wrap violations 0; work/pass mean 626,205 cycles = 3.908 VBL, min 603,028 max 691,796; period mean 5.000 VBL
race_drive mr_edge+mr_map+mr_digit+rd_geom+rd_draw+rd_init+mt_clock+mt_sync+mt_pre: 163 passes, wrap violations 0; work/pass mean 926,878 cycles = 5.784 VBL, min 587,668 max 46,117,204; period mean 6.730 VBL
race_grid: work VBL mean 3.655 p95 3.839 max 3.964 (tick 5.000); passes with work > 5 VBL: 0 of 160; period (loop top to loop top, VBL, rounded) histogram {5: 160}
race_start: work VBL mean 4.347 p95 4.675 max 4.957 (tick 5.000); passes with work > 5 VBL: 0 of 169; period (loop top to loop top, VBL, rounded) histogram {5: 169}
race_up: work VBL mean 3.908 p95 4.128 max 4.317 (tick 5.000); passes with work > 5 VBL: 0 of 169; period (loop top to loop top, VBL, rounded) histogram {5: 169}
race_drive: work VBL mean 5.784 p95 4.358 max 287.772 (tick 5.000); passes with work > 5 VBL: 2 of 163; period (loop top to loop top, VBL, rounded) histogram {4: 1, 5: 161, 288: 1}
race_drive passes with work > 4.9 VBL (key: VBL): [('2', 4.962), ('3', 5.136), ('1707', 287.772)]
keys range 1 1707 ; work VBL of the 3 passes before/after the long one: [('1704', 3.88), ('1705', 3.85), ('1706', 3.99), ('1707', 287.77)]
period outliers: [('1707', 287.78), ('1', 4.27)]
```
Reading: grid worst 3.96 VBL, driving (race_start) worst 4.96 VBL (p95 4.68), up 4.32: all under 5. Slowest passes: the two passes right after the time-out restart of race_drive (key 2: 4.96, key 3: 5.14 VBL, over by 0.14 VBL); the pass spanning the time-out itself (key 1707: 288 VBL) is the game's own time-out screen, not a race pass. The pacer on an overrun: `mt_sync` computes lag = now - NEXT; lag <= MAXLAG: no sleep, `NEXT += TICK` (the pass is late once); the next pass (3.9 VBL of work) sleeps less and the schedule is caught up (loop-top to loop-top periods: 160/160, 169/169, 169/169 passes at 5 VBL; race_drive 161 at 5, one 4 (the pass after the overrun), the 288 is the time-out screen). Lag over 2 ticks (a stall, pause) resets NEXT to now: no burst. `[INFERENCE]` for slower machines than 8 MHz STE (a 4 MHz-like case does not exist here): a scene needing more than 5 VBL runs at its own rate (tick.md).


## 5. Defaults (task 5)
`rd_geom.s`, `rd_draw.s`, `rd_init.s`: `; default: yes` (rd_init requires both). `msrpatch.py list`, default selections both validated by `verify` (below). `tools/play.sh`: `--road` kept as a no-op alias; `--extrap` = default HD set minus `mt_sync` plus `mx_pre mx_sync` (tool refuses `mt_sync` + `mx_sync`; `build --only <that set>` built clean: `payload 33216 B`, `rd_*` included, 10 patches). Other `default: no`: `mx_pre mx_sync mr_negctl test_blob36k test_framecount test_marker`.


## 6. Integrated gates (task 6)
### 6.1 verify (ALL OK) and the default builds
```
$ python3 tools/msrpatch.py verify | tail -3 ; grep dependencies
    original disk image   : 21fc00006f5a00884e42  (match)
    new                   : 4ef9000b27084e714e71
verify: ALL OK
    dependencies/conflicts/reserved RAM: checked: all pairs, both default sets, RAM free in every supported layout
```
```
$ python3 tools/msrpatch.py list   (excerpt: the default HD set's payload map, RAM reservation)

```
HD (`build/hd`) and floppy (`build/floppy`) default builds (raw):
```
HAGA+$3228    2 2412 -> 602a   [pp_bigram_cache]
built /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/hd with 9 patch(es) + 1 file patch(es); payload 26636 B at $b2700-$b8f0b
$14d98     6 5347284b1219 -> 4ef9000b3c00   [mr_digit]
$17c4a     6 49f90001058a -> 4eb9000b3040   [mr_edge]
$126d4     6 044000065347 -> 4ef9000b3400   [mr_map]
$0d128     6 52390000611b -> 4eb9000b8000   [mt_clock]
$07b0a     6 4eb900017c42 -> 4eb9000b8200   [mt_pre]
$07b74     6 4eb90000d1e4 -> 4eb9000b8100   [mt_sync]
$17c42     8 22784b8445f84ff8 -> 4ef9000b50044e71   [rd_draw]
$100b4     8 41f8456443f81bbc -> 4ef9000b40044e71   [rd_geom]
$078f6     6 4eb90000fde0 -> 4eb9000b6000   [rd_init]
```
```
disk A+$e3d0   4 7e023f07 -> 60000148   [fl_deprot]
disk A+$c350  10 21fc00006f5a00884e42 -> 4ef9000b27084e714e71   [fl_hook]
floppy: disk A 819200 B, disk B 819200 B; payload 26636 B (53 sectors) at t0.0s2x9, t50.0s1x10, t51.0s1x10, t52.0s1x10...
$14d98     6 5347284b1219 -> 4ef9000b3c00   [mr_digit]
$17c4a     6 49f90001058a -> 4eb9000b3040   [mr_edge]
$126d4     6 044000065347 -> 4ef9000b3400   [mr_map]
$0d128     6 52390000611b -> 4eb9000b8000   [mt_clock]
$07b0a     6 4eb900017c42 -> 4eb9000b8200   [mt_pre]
$07b74     6 4eb90000d1e4 -> 4eb9000b8100   [mt_sync]
$17c42     8 22784b8445f84ff8 -> 4ef9000b50044e71   [rd_draw]
$100b4     8 41f8456443f81bbc -> 4ef9000b40044e71   [rd_geom]
$078f6     6 4eb90000fde0 -> 4eb9000b6000   [rd_init]
```
(the HD tree was rebuilt once more after documentation-only edits (comments in patch sources, PATCHES.TXT text): every file except PATCHES.TXT has the same md5 as the build that was cold-booted; the floppy build is byte-identical: `work/int/hd_tested.md5`, `floppy_tested.md5`.)

### 6.2 msrabtest, default set, tick patches OFF, FIXED state ranges
`python3 tools/msrabtest.py --only mr_edge mr_map mr_digit rd_geom rd_draw rd_init --state 120` (4 snapshots x flips 10/40, per-pass state `$1000-$13ff $29c8-$34ff $4500-$4fff $dae6`):
```
patch set: mr_edge mr_map mr_digit rd_geom rd_draw rd_init  (live image edge+map+digit+rd_geom+rd_draw+rd_init.img, 22784 B)
PIXELS race_grid   at VBL 25100 flip  10: IDENTICAL  md5 81dfec87 d5a188cf (stock 81dfec87 d5a188cf)
PIXELS race_grid   at VBL 25100 flip  40: IDENTICAL  md5 7481e0c7 7481e0c7 (stock 7481e0c7 7481e0c7)
STATE  race_grid  : stock 120 passes, patched 126, common 117; 785772 bytes compared (6716 per pass); differing bytes 0 at 0 addresses
PIXELS race_start  at VBL 16400 flip  10: IDENTICAL  md5 3da506a7 c54efba9 (stock 3da506a7 c54efba9)
PIXELS race_start  at VBL 16400 flip  40: IDENTICAL  md5 90858e13 4858b4b8 (stock 90858e13 4858b4b8)
STATE  race_start : stock 126 passes, patched 121, common 121; 812636 bytes compared (6716 per pass); differing bytes 0 at 0 addresses
PIXELS race_up     at VBL 18100 flip  10: IDENTICAL  md5 64f19a1d d9cdbe0a (stock 64f19a1d d9cdbe0a)
PIXELS race_up     at VBL 18100 flip  40: IDENTICAL  md5 58491371 19ced56f (stock 58491371 19ced56f)
STATE  race_up    : stock 126 passes, patched 120, common 120; 805920 bytes compared (6716 per pass); differing bytes 0 at 0 addresses
PIXELS race_drive  at VBL 15300 flip  10: IDENTICAL  md5 d67d147e ed8944f1 (stock d67d147e ed8944f1)
PIXELS race_drive  at VBL 15300 flip  40: IDENTICAL  md5 3d3df84c 3d3df84c (stock 3d3df84c 3d3df84c)
STATE  race_drive : stock 126 passes, patched 121, common 121; 812636 bytes compared (6716 per pass); differing bytes 0 at 0 addresses
RESULT: ALL IDENTICAL
```
Negative control (`mr_negctl` added, race_start flip 10):
```
patch set: mr_edge mr_map mr_digit rd_geom rd_draw rd_init mr_negctl  (live image a57fc0720c.img, 22784 B)
PIXELS race_start  at VBL 16400 flip  10: DIFFER (1334 bytes of 64000)  md5 017bcc0f 86c744b8 (stock 3da506a7 c54efba9)
RESULT: DIFFERENCES FOUND
```

### 6.3 Per-pass state, tick patches ON (T=30): section 4 (164 passes race_start, 230 race_drive incl. time-out/restart; 0 differing bytes).

### 6.4 Cold boots to the race, default HD build (`work/int/cold_int.py`: cold boot, SPACE navigation, SPACE into the race loop, then marker, clock, road magic `RDG1` and `WPTR`; `$100e` samples 4 s apart = about 46 passes, i.e. 10 per emulated second):
```
ste TOS 1.62 1024 KB: boot_to_race True vbl 5812
  race: $1021 2 $100e samples [0, 25, 71, 117] vbl 6803
  marker   000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
  CLK/NEXT/PEND 000B8F00: 00 00 21 54 00 00 21 5a 00 00 00 00              ..!T..!Z....
  RDG1 $d0000 000D0000: 52 44 47 31 00 0a 00 00                          RDG1....
  WPTR $e7040  000E7040: 00 01 02 ba                                      ...´
  $135a 0000135A: 00 01 02 ba                                      ...´
ste TOS 1.62 4096 KB: boot_to_race True vbl 5808
  race: $1021 2 $100e samples [0, 26, 72, 118] vbl 6799
  marker   000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
  CLK/NEXT/PEND 000B8F00: 00 00 21 6c 00 00 21 84 00 00 00 00              ..!l..!ä....
  RDG1 $d0000 000D0000: 52 44 47 31 00 0a 00 00                          RDG1....
  WPTR $e7040  000E7040: 00 01 02 ba                                      ...´
  $135a 0000135A: 00 01 02 ba                                      ...´
megaste TOS 2.06 4096 KB: boot_to_race True vbl 6045
  race: $1021 2 $100e samples [6, 52, 98, 144] vbl 7234
  marker   000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
  CLK/NEXT/PEND 000B8F00: 00 00 22 97 00 00 22 b0 00 00 00 00              .."ù.."ã....
  RDG1 $d0000 000D0000: 52 44 47 31 00 0a 00 00                          RDG1....
  WPTR $e7040  000E7040: 00 01 02 ba                                      ...´
  $135a 0000135A: 00 01 02 ba                                      ...´
st TOS 1.04 1024 KB: boot_to_race True vbl 5809
  race: $1021 2 $100e samples [0, 25, 71, 117] vbl 6800
  marker   000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
  CLK/NEXT/PEND 000B8F00: 00 00 21 54 00 00 21 5a 00 00 00 00              ..!T..!Z....
  RDG1 $d0000 000D0000: 52 44 47 31 00 0a 00 00                          RDG1....
  WPTR $e7040  000E7040: 00 01 02 ba                                      ...´
  $135a 0000135A: 00 01 02 ba                                      ...´
tt TOS 3.06 4096 KB: boot_to_race True vbl 5882
  race: $1021 2 $100e samples [24, 70, 116, 162] vbl 7071
  marker   000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
  CLK/NEXT/PEND 000B8F00: 00 00 23 91 00 00 23 a5 00 00 00 00              ..#...#.....
  RDG1 $d0000 000D0000: 52 44 47 31 00 0a 00 00                          RDG1....
  WPTR $e7040  000E7040: 00 01 02 ba                                      ....
  $135a 0000135A: 00 01 02 ba                                      ....
```
### 6.5 Floppy build (`tools/msrfloppy.py gate`, disk A alone, SPACE through the intro, disk-2 swap, race; the gate prints the marker, the tick clock and (added) the road magic/WPTR after 30 s in the race):
`ste_1024`:
```
first mode-2 (story) screen: /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/shots/floppy_int_ste_1024/05_vbl2298.png $1021/$100e (2, 0) vbl 2298
disk-2 prompt True t 46 vbl 2409 story screen seen True screens saved 6 in /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/shots/floppy_int_ste_1024
prompt shot /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/shots/floppy_int_ste_1024_prompt.png
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
after swap: vbl 4096 $1021/$100e (2, 219)
race shot /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/shots/floppy_int_ste_1024_race.png
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
tick clock $b8f00: 000B8F00: 00 00 32 9a 00 00 32 b2                          ..2Ü..2Ø
road magic $d0000: 000D0000: 52 44 47 31 00 0a 00 00                          RDG1....  WPTR $e7040: 000E7040: 00 01 02 ba                                      ...´
log: /tmp/strun-uabq52md/log.txt
```
`ste_4096`:
```
first mode-2 (story) screen: /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/shots/floppy_int_ste_4096/04_vbl2038.png $1021/$100e (2, 0) vbl 2038
disk-2 prompt True t 46 vbl 2410 story screen seen True screens saved 6 in /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/shots/floppy_int_ste_4096
prompt shot /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/shots/floppy_int_ste_4096_prompt.png
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
after swap: vbl 4096 $1021/$100e (2, 215)
race shot /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/shots/floppy_int_ste_4096_race.png
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
tick clock $b8f00: 000B8F00: 00 00 33 72 00 00 33 84                          ..3r..3ä
road magic $d0000: 000D0000: 52 44 47 31 00 0a 00 00                          RDG1....  WPTR $e7040: 000E7040: 00 01 02 ba                                      ...´
log: /tmp/strun-lzlqrlgm/log.txt
```
`megaste_4096`:
```
first mode-2 (story) screen: /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/shots/floppy_int_megaste_4096/05_vbl2456.png $1021/$100e (2, 8) vbl 2456
disk-2 prompt True t 46 vbl 2902 story screen seen True screens saved 7 in /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/shots/floppy_int_megaste_4096
prompt shot /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/shots/floppy_int_megaste_4096_prompt.png
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
after swap: vbl 4925 $1021/$100e (2, 213)
race shot /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/shots/floppy_int_megaste_4096_race.png
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
tick clock $b8f00: 000B8F00: 00 00 33 e0 00 00 33 f9                          ..3α..3∙
road magic $d0000: 000D0000: 52 44 47 31 00 0a 00 00                          RDG1....  WPTR $e7040: 000E7040: 00 01 02 ba                                      ...´
log: /tmp/strun-kka6qluq/log.txt
```
`st_1024_tos104`:
```
first mode-2 (story) screen: /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/shots/floppy_int_st_1024_tos104/04_vbl2036.png $1021/$100e (2, 0) vbl 2036
disk-2 prompt True t 46 vbl 2408 story screen seen True screens saved 6 in /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/shots/floppy_int_st_1024_tos104
prompt shot /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/shots/floppy_int_st_1024_tos104_prompt.png
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
after swap: vbl 4095 $1021/$100e (2, 215)
race shot /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/shots/floppy_int_st_1024_tos104_race.png
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
tick clock $b8f00: 000B8F00: 00 00 33 54 00 00 33 72                          ..3T..3r
road magic $d0000: 000D0000: 52 44 47 31 00 0a 00 00                          RDG1....  WPTR $e7040: 000E7040: 00 01 02 ba                                      ...´
log: /tmp/strun-8ofezx5c/log.txt
```

### 6.6 5-minute play, STE 1 MB, default HD build (`work/int/play5_int.py`: cold boot + SPACE + joystick `up` held via `$6105`, 16,681 VBL = 334 s; samples `(VBL, $1021, $100e, $1226)`):
```
in_race True vbl 5808
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....  CLK/NEXT/PEND $b8f00: 000B8F00: 00 00 0a 68 00 00 00 00 00 00 00 00              ...h........
after SPACE: $100e 0 7b74 hits/100vbl {'vbls': 100, 'flips': 20, 'fps': 10.0, 'vbl_per_frame': 5.0}
(581, 2, 180, 0)
(1252, 2, 314, 0)
(1923, 2, 449, 0)
(2593, 2, 583, 0)
(3264, 2, 717, 0)
(3935, 2, 851, 0)
(4606, 2, 985, 0)
(5277, 2, 1115, 0)
(5948, 2, 1249, 0)
(6618, 2, 1383, 0)
(7289, 2, 1517, 0)
(7960, 2, 1651, 5)
(8631, 2, 25, 0)
(9302, 2, 159, 0)
(9973, 2, 293, 0)
(10643, 2, 427, 0)
(11314, 2, 561, 0)
(11985, 2, 695, 0)
(12656, 2, 830, 0)
(13327, 2, 964, 0)
(13998, 2, 1098, 0)
(14669, 2, 1232, 0)
(15339, 2, 1366, 0)
(16010, 2, 1500, 0)
(16681, 2, 1635, 0)
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....  CLK/NEXT/PEND: 000B8F00: 00 01 a3 f4 00 01 a4 12 00 00 00 00              ..ú⌠..ñ.....
alive, fc advancing: 1671
road $d0000: 000D0000: 52 44 47 31 00 0a 00 00                          RDG1.... WPTR: 000E7040: 00 01 02 ba                                      ...´
```
Race at 10.0 passes/s (about 134 passes per 671 VBL), time-out (`$1226` = 5 at `$100e` 1651), restart (`$100e` 25 at the next sample), no crash, marker `MSPO`, road tables present.

### 6.7 60 Hz
Snapshot runs (section 4 speed table, `$ff820a` = `$fc`): patched 10.000 passes per 60 Hz second at 8 and 32 MHz (6.000 VBL/pass) in driving and on the grid. Not a native 60 Hz cold boot, not the road generation at 60 Hz (`[INFERENCE]`: pure CPU work).


## 7. Unproven, risks, decisions for the lead
- Hatari only. No real hardware, no Falcon, no 2 MB, no native 60 Hz boot, no Mega ST/MSTE 1 MB cold boot with the final set (Mega STE 4 MB booted).
- Tracks: only the first track was captured offline and played; tracks 5, 12 and 14 were reached by poking `$102c` before the time-out restart (the game's own replay path) and compared stock vs patched at two flips each (IDENTICAL); not a won-race campaign progression, not all 15 tracks.
- A pass can overrun the 5-VBL tick: `race_start` has a worst pass at 4.96 VBL (4 % of a tick headroom) and the two passes after a restart reach 5.14 VBL; they run late once and the pacer catches up (no visible stutter measured, but no per-flip display timing was captured). A heavier scene (more cars, hills with collisions) could overrun more often `[INFERENCE]`; the rule is stated in `tick.md` (late, never bursts).
- The race setup now stalls about 20 VBL (0.4 s at 50 Hz) at the very first race of a session (and 13 VBL when the colour table changes), before the race loop, while the screen shows what the game showed at the end of the setup; it is no longer inside the race. Decision for the lead: acceptable?
- `mx_*` stays off (needs the user's approval for the visible extra frames). `mx_sync` + `rd_*` build together by the tool's check (no overlap), the pair was not gated.
- Credit patch, user docs, packaging, blitter/clouds decisions: `PLAN.md`.


## 8. Extra frames on the integrated build (task: ship `mx_*` by default)
Owner: this wave. Machine for every number: Hatari 2.6.1, `build/mx_hd` (the default HD set) unless named; snapshots are stock-game states, the patch set is applied live (`msrpatch.py live`) at the first pass, so stock and patched runs differ only by the patches. Raw outputs: `work/int/mx/res/` (scripts and helper library: `work/int/mx/{mxlib,exp_state,pixcap,pixcmp,cmpstate,exp_rate,cold,play5,flips,kgate,dumplevel}.py`). `[INFERENCE]` marks what no tool output here proves.

### 8.1 What had to change for the integrated build
`mx_sync.s`: `TICK equ 36` -> **30** (the prototype was written for the old 8.33 passes/s tick; `mt_sync` is at 30 since the T=30 wave, and `mx_sync` replaces it, so the extras' fraction `f = (display - main display)/TICK` and the deadline rule must use the same tick). Nothing else in `mx_sync`/`mx_pre` was tick-dependent; every other assumption of `extrap.md` was re-checked on the integrated set:
* **Road tables and `rd_*` state across extras**: the extras call `$100b4` (rd_geom, `$B4004`) and `$17c42` (rd_draw, `$B5004`) exactly where the pass calls them, with the same inputs. `rd_geom`'s standing-frame reuse is keyed on the 33 generator words (`$13ae/$13b0..`, `$1bba/$1bbc`, `$23c6/$23c8`, `$131c`, `$1320`); the extras advance those generators, so the next main frame's key never matches a stale saved copy: it recomputes (the extras leave `$130c` = the tick's speed and `restoreundo` restores the generator windows). `rd_draw`'s window tables are keyed on the colour-table pointer (`WPTR`) and rebuilt after a colour change (`rd_init` pre-warms them), independent of pose. Verified by the state gates below (the whole geometry output `$4724-$4f77` and the generator words are inside the compared ranges and are masked only as "rewritten before use", see 8.2) and by the main-frame pixel gates (8.3).
* **`$13a0` (far-colour reload) fallback**: `rd_draw` runs the stock loop when `$13a0 != 0`; the extras go through the same entry, so the fallback is taken identically. `$13a0 = 0` in every dump (`road.md` section 1), so this path is not exercised by any real frame here (unchanged from the previous wave, `[INFERENCE]` for the fallback).
* **Stock fallback paths of `rd_draw`** (rows it does not cover hand the rest of the frame to `$17c66`): same entry for extras and main frames, and the state gate covers `$4724-$4f77` + `$12f0-$1307` for both.
* **8 MHz STE unchanged**: `wantnext` measures the time left in the tick and `mx_pre` skips the 2.7 KB slot copy when no extra frame fits (`NOWANT`): at 8 MHz the extra-frame code costs one byte test + the copy skip per pass. Measured: 0 extras at 8 MHz, pass rate and position rate identical to `mt_sync` (8.4), and the state/pixel gates at 8 MHz are identical to the `T` (fixed tick, no extras) build.

### 8.2 State gates (per-pass game state, stock vs mx)
Recipe: `work/int/mx/exp_state.py` = the `work/extrap/exp_state_mx.py` recipe (breakpoint at `$7b86`, keyed by `$100e`) with the msrabtest ranges `$1000-$13ff, $29c8-$34ff, $4500-$4fff, $dae6` plus the ring/state windows `$1bb0 $23bc $27c8`, `$3500-$36ff` and the blob counters; `cmpstate.py` applies the documented display-scratch mask (below). `[M]`
```
A ste1m_race_start.sav 8 hits 263 bytes/hit 7306 extra frames in window 0
T ste1m_race_start.sav 8 hits 263 bytes/hit 7306 extra frames in window 0
X ste1m_race_start.sav 8 hits 263 bytes/hit 7306 extra frames in window 0
X ste1m_race_start.sav 16 hits 265 bytes/hit 7306 extra frames in window 209
X ste1m_race_start.sav 32 hits 265 bytes/hit 7306 extra frames in window 694
A ste1m_race_drive.sav 8 hits 279 bytes/hit 7306 extra frames in window 0        (a 520-pass run with 'up' held at every pass:
T ste1m_race_drive.sav 8 hits 271 bytes/hit 7306 extra frames in window 0         time-out and restart inside)
X ste1m_race_drive.sav 8 hits 280 bytes/hit 7306 extra frames in window 0
X ste1m_race_drive.sav 16 hits 276 bytes/hit 7306 extra frames in window 2
X ste1m_race_drive.sav 32 hits 277 bytes/hit 7306 extra frames in window 0
A ste1m_race_drive.sav 8 hits 522 bytes/hit 7306 extra frames in window 0        ('driveup450' run, 520 passes)
X ste1m_race_drive.sav 16 hits 524 bytes/hit 7306 extra frames in window 2
X ste1m_race_drive.sav 32 hits 527 bytes/hit 7306 extra frames in window 0
```
Comparisons (`cmpstate.py`, mask on; the "A" side is the stock game):
```
res/st_start_A8.json (263 passes) vs res/st_start_T8.json (263): common 257 (keys 95..351); 1874558 bytes compared; differing addresses 0, differing bytes 0
res/st_start_A8.json (263 passes) vs res/st_start_X8.json (263): common 257 (keys 95..351); 1874558 bytes compared; differing addresses 0, differing bytes 0
res/st_start_A8.json (263 passes) vs res/st_start_X16.json (265): common 243 (keys 109..351); 1772442 bytes compared; masked differing bytes 46623; differing addresses 0, differing bytes 0
res/st_start_A8.json (263 passes) vs res/st_start_X32.json (265): common 242 (keys 110..351); 1765148 bytes compared; masked differing bytes 69837; differing addresses 0, differing bytes 0
res/st_driveup_A8.json (279 passes) vs res/st_driveup_T8.json (271): common 271 (keys 0..1706); differing addresses 0
res/st_driveup_A8.json (279 passes) vs res/st_driveup_X8.json (280): common 278 (keys 0..1706); differing addresses 0
res/st_driveup_A8.json (279 passes) vs res/st_driveup_X16.json (276): common 265 (keys 0..1706); differing addresses 0
res/st_driveup_A8.json (279 passes) vs res/st_driveup_X32.json (277): common 262 (keys 0..1706); differing addresses 0
res/st_driveup450_A8.json (522 passes) vs res/st_driveup450_X16.json (524): common 508 (keys 0..1706); 3705352 bytes compared; differing addresses 0
res/st_driveup450_A8.json (522 passes) vs res/st_driveup450_X32.json (527): common 506 (keys 0..1706); 3690764 bytes compared; differing addresses 0
```
`race_drive` keys 0..1706 with the restart inside (the counter wraps 1706 -> 0), so the ">= 190 passes incl. time-out and restart" requirement is met by the 508/506-pass runs. The masked bytes are exactly the five documented categories (raw per-category counts, e.g. X16 start):
```
   masked: 250 differing bytes in buffer parity/pointer $1004-$100d
   masked: 1540 differing bytes in cloud $28/$2a display history, 12 entries
   masked: 48 differing bytes in object order list scratch $36e8-$36ff
   masked: 363 differing bytes in raster scratch $12f0-$1307
   masked: 44422 differing bytes in road geometry output $4724-$4f77 (rewritten before use)
```
The same ranges as `tools/msrabtest.py --state` (no mask): that tool cannot be used for `mx_*` as it stands for two reasons, both verified: it has no CPU-clock option (8 MHz => 0 extras) and it compares those ranges byte-for-byte including the display scratch (`$1004-$100d` parity, `$12f0-$1307` raster bands, `$4724-$4f77` geometry output, cloud `$28/$2a`, order-list scratch), which the extra frames necessarily rewrite (they are the patches' display side, not game state; with `T`/stock the same ranges give 0). The recipes are otherwise identical (`$7b86`, keyed by `$100e`, same ranges).

### 8.3 Main frames pixel-identical to stock
Fresh captures (not the prototype's emulator-only shots): `work/int/mx/pixcap.py` saves the **drawn** main-frame buffer (pointer read at the single per-pass `$7b74` gate, before the flip; extras never reach `$7b74`, so every capture is a main frame) for 200-520 consecutive passes; `pixcmp.py` compares the frame of the same pass number. Raw: `res/pix_cmp.txt`, `res/emu_pix_levels.txt`.
```
pix/start_A8 vs pix/start_T8: 200 / 200 passes, common 198 main frames compared, differing 0, worst 0 bytes
pix/start_A8 vs pix/start_X8: 200 / 200 passes, common 199 main frames compared, differing 0, worst 0 bytes
pix/start_A8 vs pix/start_X16: 200 / 200 passes, common 180 main frames compared, differing 0, worst 0 bytes
pix/start_A8 vs pix/start_X32: 200 / 200 passes, common 178 main frames compared, differing 0, worst 0 bytes
pix/driveup_A8 vs pix/driveup_T8: 230 / 230 passes, common 228 main frames compared, differing 0, worst 0 bytes
pix/driveup_A8 vs pix/driveup_X8: 230 / 230 passes, common 228 main frames compared, differing 0, worst 0 bytes
pix/driveup_A8 vs pix/driveup_X16: 230 / 230 passes, common 210 main frames compared, differing 0, worst 0 bytes
pix/driveup_A8 vs pix/driveup_X32: 230 / 230 passes, common 212 main frames compared, differing 0, worst 0 bytes
pix/f60_A8 vs pix/f60_T8: 200 / 200 passes, common 198 main frames compared, differing 0
pix/f60_A8 vs pix/f60_X16: 200 / 200 passes, common 180 main frames compared, differing 0
pix/f60_A8 vs pix/f60_X32: 200 / 200 passes, common 182 main frames compared, differing 0
negative control (stock pass k vs stock pass k+1): [3061, 2762, 3167, 3707, 3238, 3299, 6678, 3530, 3860, 7090] bytes differ
```
Track 1 (the shipped first track) is identical in every compared frame at 8/16/32 MHz and at 60 Hz. **Documented tolerance (user-approved, Main decision):** on other tracks, main frames can differ from stock by 1-2 bytes (2-10 pixels) at the cloud / mountain-silhouette edge in the sky rows. Measured (hatari, `pix/L5_*`, `pix/L12_*`; and the emulator over all 15 levels, 130 passes x two inputs each, `res/emu_pix_levels.txt`):
```
L5  up:   44 of 130 frames, worst 1 byte   | L5  zig: 0     | L6 up: 44, worst 1  | L8 zig: 44, worst 1
L12 up:    1 of 130 frames, worst 2 bytes  | L12 zig: 1, worst 5 | L13 up: 2, worst 4 | L14 zig: 20, worst 10
L0-L4, L7, L9, L10, L11: 0 in both inputs
  (hatari, poked tracks after the restart, 500/311 frames post-restart: L5 106 of 500 frames 1 byte; L12 1 of 311 frames 2 bytes)
```
Exact set and timing (per case: level, input, buffer, rows, x, stock vs mx colour, passes; and whether extra frames show it): **`work/extrap/residue/summary.md` + `residue.tsv`/`extras.tsv`** (`work/int/mx/residue2.py`, exact emulator, 130 passes per case; the HUD build's cloud removal / first-frame wipe can be verified against it: the expected result is `residue pixels 0` on every level, and the rows that ever carried residue are 25-29, 63, 72-74 and 85-86 - **not only rows 0-64**). Extras show the residue at least as often as main frames (L12: 1 main frame, 130 extra frames).
Cause (emulator-reproduced, also with zero-advance extras, `work/int/mx/dx.py`/`dx2.py`/`dx3.py`): the cloud erase `$122e4` is an OR of the inverse background mask into the buffer, and the cloud draw ANDs over non-sky pixels; where a cloud crosses the mountain silhouette the sky rows of each buffer keep the result of the *draw history* (edge pixels are eroded and never restored). Stock's two buffers see alternating frames; with extras they see a different sequence, so a pixel at the silhouette edge can end up 14 vs 15. Not game state (state gates 8.2 are 0), not visible at normal speed, and it disappears when the clouds are removed (the planned HUD build drops `de1c`/`de6c`; the extras' `$dd50` call and the private `hud:` list are marked in `mx_sync.s` for that).
The L5/L12 hatari runs also show a separate, larger pre-restart difference in the message text colour (passes 1661-1705, 314 bytes): those runs poke `$102c` at the apply instant, and the two runs' apply instants fall on different passes (8 vs 16/32 MHz), so the old level's on-screen message was drawn from a different message table before the restart. It is an artifact of poking a mid-run level change into two differently paced runs, not of the extras (the same frames in the unpoked `driveup` runs are identical).

### 8.4 Frames per second and pass rate (600 VBL windows, CPU halted at both ends)
`work/int/mx/exp_rate.py` (same recipe as `work/extrap/exp_mx.py` + the integrated patch list); snapshot = stock race start, driving. Raw: `res/rates_50hz.txt`, `res/rates_60hz.txt`, `res/rates_grid.txt`.
```
variant  MHz  passes  extra  pass/s   fps    pos/s
A(stock)  8    100      0     8.333   8.333  83.33
A        16    200      0    16.667  16.667 166.67
A        32    200      0    16.667  16.667 166.67
T(=integrated, no extras)
T         8    120      0    10.000  10.000 100.00
T        16    120      0    10.000  10.000 100.00
T        32    120      0    10.000  10.000 100.00
X(=integrated + mx, the default)
X         8    120      0    10.000  10.000 100.00   (skip reason 0 = no slot copy: 120/120)
X        16    120    114    10.000  19.500 100.00
X        32    120    365    10.000  40.417 100.00
60 Hz:
A         8     85      0     8.500   8.500  85.00
A        32    200      0    20.000  20.000 198.30
T         8    100      0    10.000  10.000 100.00
T        32    100      0    10.000  10.000 100.00
X         8    100      0    10.000  10.000 100.00
X        32    100    200    10.000  30.000 100.00
grid (standing, extras correctly skipped: reason 2 "standing"):
X         8/16/32 120  0    10.000  10.000   0.00
```
Reading: the extra frames do not change the game speed (10.000 passes/s and 100.0 world units/s at every clock, the stock STE rate) and add 0 / ~1 extra per pass (16 MHz) / ~3 (32 MHz) pictures. On the grid nothing changes (`$130c = 0`).

### 8.5 Cold boots, floppy, Falcon, native 60 Hz
Default HD build `build/mx_hd` (= `build/hd`, 10 patches + `pp_bigram_cache`, 33,216 B payload), cold boot, SPACE to the race, 'up' held, three windows per machine (`work/int/mx/cold.py`; raw `res/cold.log`). Extras counted from the blob counters (`NFRAMES` at `$b8f38`), not from screenshots:
```
ste 1024 TOS 1.62 native 8 MHz : 170 passes, 9.988/s, extras 0      (skip reason 0 = no slot copy, 170/170)
                    16 MHz      : 171 passes, 10.047/s, extras 197  -> 21.6 fps displayed
                    32 MHz      : 171 passes, 10.047/s, extras 627  -> 46.9 fps displayed
ste 4096 TOS 1.62 native      : 170 passes, extras 0 ; 16 MHz 196 ; 32 MHz 625
megaste 4096 TOS 2.06 ($ff820a = fc = 60 Hz): 170 passes in 17.0 s = 10.0/s, extras 0 ; 16 MHz 55 ; 32 MHz 340
st 1024 TOS 1.04 native      : 170 passes, extras 0 ; 16 MHz 197 ; 32 MHz 627
tt 4096 TOS 3.06 ($ff820a = 01 = 60 Hz, 32 MHz native): 170 passes in 17.0 s = 10.0/s, extras 458 (30.8 fps) ; 16 MHz 193 ; 32 MHz 617
falcon 4096 TOS 4.04 ($ff820a = 02 = 50 Hz), native 16 MHz: 170 passes, 10.0/s, extras 184 (20.8 fps) ; 16 MHz 226 ; 32 MHz 644
falcon EmuTOS: boot_to_race False (the EmuTOS boot does not autostart PP's loader; not used, TOS 4.04 is present)
each boot: marker $b2700 = "MSPO", sites $d128/$7b0a/$7b46/$7b74 patched, $1021 = 2, road magic RDG1, WPTR = $102ba
```
So the **native 60 Hz** case is a real ROM/Hatari 60 Hz boot (no forcing): the Mega STE 2.06 and the TT 3.06 boots read `$ff820a` bit 1 = 0 and run exactly 6 clock units per VBL; the pass rate stays 10.0 per second and the TT/Falcon draw extras at their own clock. `mx_sync` reads `$ff820a` per group (`VBLU` = 6 at 50 Hz, 5 at 60 Hz) and the deadline rule uses the same clock, so both refresh rates work; the 60 Hz state/pixel gates in 8.2/8.3 were run with `$ff820a` forced to 60 Hz on the STE snapshot (the only 60 Hz-equivalent source-state I have that the pacer can be measured on; `[INFERENCE]` that forced-60 Hz equals a true 60 Hz machine for the pacer, since the pacer reads only `$ff820a` and the 1/300 s clock).
Floppy gate (`tools/msrfloppy.py gate`, now with `--cpu`: after the race starts it raises the clock, holds 'up' and prints the blob counters; `build/floppy`, raw `res/rest.log`): STE 1 MB, STE 4 MB, Mega STE 4 MB, ST 1 MB all boot through the story screens, the disk-2 swap and into the race with marker/clock/road tables, extras 344/343/391/352 frames at 16 MHz.

### 8.6 Kernel-table check on a second track
`KTAB` (the 100 sprite-kernel longs `mx_sync` restores, `extrap.md` section 6) was captured from one race on track 1. Re-checked two ways now:
* **Emulator, all 15 levels**: RAM dumps at the race loop of each level (`work/int/mx/dumplevel.py`: snapshot `race_drive`, `$102c` poked, 'up' held through the restart, `savebin` at the first pass with `$130c > 6`), then stock vs mx (X_TEST=3 extras) per pass over the whole code/state area `$1000-$7ffff` minus the documented display scratch, for 120-130 passes: `differing bytes 14; runs 7b0d-7b0f, 7b49-7b4b, 7b77-7b79, d128-d129, d12b-d12d` = only the patch sites themselves (`mt_pre`, `mx_pre`, `mx_sync`, `mt_clock`), on every level (`res/kgate_L5.txt`, and the same run per level).
* **Hatari, tracks 5 and 12 after the time-out restart** (`$102c` poked as MSRIntegrate did): with the kernel region `$12000-$15000` + `$dafe` added to the compared ranges, the only differing addresses are the four patch sites and the message colour artifact of 8.3 (raw in `res/gate` logs of `st_L5_*`/`st_L12_*`): no self-modified code byte differs.
So on the 15 reachable levels the extra frames leave no stale kernel immediate behind. `[INFERENCE]`: a level 15+ or a scenery object not visited by 130 passes of that dump could patch another long; the failure mode is a few bytes of one main frame (stock's own stale-immediate quirk), never game state.

### 8.7 Frames per second, pass rate, and the visible result
Rate table: 8.4. Displayed pictures per second with the default build: 10 (8 MHz), 19.5 (16 MHz), 40.4 (32 MHz) at 50 Hz; 10 / 30 at 60 Hz (measured, `res/rates_*`). Game speed is 10.0 passes/s = 100 world units/s at every clock (8.4), i.e. the user-approved 20 % above the stock 8 MHz rate and no longer CPU-clock scaled.
Screenshots of consecutive frames (`work/int/mx/flips.py`: captures the drawn buffer at every flip, main and extra, decodes with the game palettes; sheets `work/extrap/ab/mx16_flips.png`, `work/extrap/ab/mx32_flips.png`, raw PNGs + `meta.json` in `work/extrap/ab/mx16/`, `mx32/`):
```
X 16 MHz: flips captured 8 [(16336,118),(16339,119),(16341,119),(16344,120),(16346,120),(16349,121),(16351,121),(16354,122)]   (VBL, pass)
X 32 MHz: flips captured 8 [(16336,121),(16337,121),(16338,121),(16340,122),(16341,122),(16342,122),(16343,122),(16345,123)]
```
At 16 MHz a main frame and one extra alternate every 2-3 VBL (positions 458, 468, 468, 478, 478, 488: the logic position advances per pass, the extra frames show the interpolated pose); at 32 MHz the flip interval is 1-2 VBL (3 extras per pass). The sheets show the road/scenery moving between the logic positions with no flicker or tearing (the extra frames wait for the previous flip's latch before their first back-buffer write, as the main frame does via `mt_pre`); one 3-VBL main interval appears where the pacer was catching up after a late pass (the documented `tick.md` rule).

### 8.8 5-minute play
`work/int/mx/play5.py`: cold boot of `build/mx_hd`, SPACE, 'up' held (re-applied every sample: the restart clears the input byte), 16,700 VBL, sampling `($1021, $100e, $1226, extra counters)`; race start, time-out `$1226 = 5`, restart, no crash, marker/road tables intact, extras counted from `$b8f38`. Raw: `res/play16.log`.

### 8.9 Defaults and launcher
`mx_pre`, `mx_sync`: `default: yes`; `mt_sync`: `default: no` (same site, declared conflict -> exactly one pacer in every default set). `msrpatch.py list` prints `mx_sync yes $07b74 ... $b8100,$b8380,$b8400 / $b8f04+4,$b8f20+224,$b9000+3584` and `mt_sync no`. `verify: ALL OK`; the default HD build (`build/hd`, 10 patches + `pp_bigram_cache`, payload 33,216 B at `$b2700-$ba8bf`) and the floppy build (`build/floppy`, 65 sectors) select `mx_*` (raw section 8.5, 8.8); `[mt_sync]`-only build still verifies and is what `play.sh --noextrap` uses. `tools/play.sh`: `--extrap` is a no-op alias, `--noextrap` builds the fixed-tick-only variant (HD and floppy). `patches/README.md` 72-74 and `PLAN.md` updated.

### 8.10 Unproven / notes
* Real hardware: none of this was run on a real 16/32 MHz machine (Mega STE cache behaviour included).
* 60 Hz: state/pixel equality measured with `$ff820a` forced (8.2/8.3); the *native* 60 Hz evidence is the rate + extras counts of the Mega STE 2.06 and TT 3.06 cold boots (8.5).
* Falcon: TOS 4.04 boots and runs (native 16 MHz, 10.0 passes/s, extras 184/226/644 frames at 16/16/32 MHz); EmuTOS does not autostart PP's loader.
* The pre-restart message-colour difference of the poked-track runs (8.3) is an artifact of the poke timing, not shipped behaviour; the unpoked gates are identical.
* `[INFERENCE]` that a forced-60 Hz STE equals a 60 Hz machine for the pacer.

## 9. New HUD and no clouds (MSRHudBuild): default set changed
`hd_stage hd_init hd_clouds hd_nomap hd_nomap2` are now default (visible change, user-approved layout A); `mr_map mr_digit` are `default: no` (dead code with the new HUD); `mx_sync` requires `hd_stage` (its extra frames call the new TOPBAR, the private HUD call list, the `dd50` call and the HUD flag undo ranges are gone). Default payload 47,360 B (`$B2700-$BDFFF`).
The earlier statements in this note about cloud-edge residue (<= 2 bytes on some tracks), `mx_sync`'s HUD call list and the pixel-identical default set apply to the previous default set only. Evidence, gates and numbers: `work/notes/hud_build.md`.
