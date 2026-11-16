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

