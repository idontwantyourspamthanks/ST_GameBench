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
So the **native 60 Hz** case is a real ROM/Hatari 60 Hz boot (no forcing): the Mega STE 2.06 (**4 MB only**, relabel MSRMegaSTE) and the TT 3.06 boots read `$ff820a` bit 1 = 0 and run exactly 6 clock units per VBL; the pass rate stays 10.0 per second and the TT/Falcon draw extras at their own clock. `mx_sync` reads `$ff820a` per group (`VBLU` = 6 at 50 Hz, 5 at 60 Hz) and the deadline rule uses the same clock, so both refresh rates work; the 60 Hz state/pixel gates in 8.2/8.3 were run with `$ff820a` forced to 60 Hz on the STE snapshot (the only 60 Hz-equivalent source-state I have that the pacer can be measured on; `[INFERENCE]` that forced-60 Hz equals a true 60 Hz machine for the pacer, since the pacer reads only `$ff820a` and the 1/300 s clock).
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
* 60 Hz: state/pixel equality measured with `$ff820a` forced (8.2/8.3); the *native* 60 Hz evidence is the rate + extras counts of the Mega STE 2.06 (4 MB only) and TT 3.06 cold boots (8.5).
* Falcon: TOS 4.04 boots and runs (native 16 MHz, 10.0 passes/s, extras 184/226/644 frames at 16/16/32 MHz); EmuTOS does not autostart PP's loader.
* The pre-restart message-colour difference of the poked-track runs (8.3) is an artifact of the poke timing, not shipped behaviour; the unpoked gates are identical.
* `[INFERENCE]` that a forced-60 Hz STE equals a 60 Hz machine for the pacer.

## 9. New HUD and no clouds (MSRHudBuild): default set changed
`hd_stage hd_init hd_clouds hd_nomap hd_nomap2` are now default (visible change, user-approved layout A); `mr_map mr_digit` are `default: no` (dead code with the new HUD); `mx_sync` requires `hd_stage` (its extra frames call the new TOPBAR, the private HUD call list, the `dd50` call and the HUD flag undo ranges are gone). Default payload 47,360 B (`$B2700-$BDFFF`).
The earlier statements in this note about cloud-edge residue (<= 2 bytes on some tracks), `mx_sync`'s HUD call list and the pixel-identical default set apply to the previous default set only. Evidence, gates and numbers: `work/notes/hud_build.md`.

## 10. Mega STE 1 MB (MSRMegaSTE): the 2 bombs, the TOS 2.06 1 MB layout, `rd_*` relocated
Machine: Hatari 2.6.1, headless harness, `--fast-boot yes`, cycle-exact (the user's `~/.config/hatari/hatari.cfg`). Scripts: `work/mste/boot.py` (cold boot of a build to the race), `work/mste/tosonly.py` (TOS only, empty C:), `work/mste/racedump.py`; raw outputs `work/mste/*.txt`. `[INFERENCE]` marks what no output here proves.
**Earlier "Mega STE 2.06" gates in these notes were all 4 MB (and the floppy one 4 MB): none exercised the 1 MB TOS 2.06 layout or a 1 MB Mega STE boot at all.**

### 10.1 The 2 bombs: TOS 2.06 at power-on at 16 MHz with 1 MB, before any game code (`--cpuclock 16`)
`tools/play.sh --machine megaste` boots at 8 MHz (default `--cpu 8`) and does NOT bomb (below); `--cpu 16` passes `--cpuclock 16` to Hatari, i.e. TOS 2.06 starts at 16 MHz, and TOS bombs in its own init.
```
# full default HD build (build/mste_hd), cold boot to the race, `python3 work/mste/boot.py megaste RAM 2.06 build/mste_hd CLOCK`
megaste 1024 KB  8 MHz: in_race=True vbl=6046   $b2700 = 4d 53 50 4f (MSPO)      (also with --sound 44100 --joy1 keys, the exact play.sh options: vbl=6046, MSPO)
megaste 2048 KB 16 MHz: in_race=True vbl=6047   MSPO
megaste 4096 KB  8 MHz: in_race=True vbl=6047   MSPO
megaste 1024 KB 16 MHz: in_race=False vbl=24261 $b2700 = 00 00 ... (payload never copied)
    WARN : Bus Error reading at address $f00000, PC=$e21696 addr_e3=e21696 op_e3=3019      (125 times in the log)
# bisect at 1 MB / 16 MHz, same command (raw work/mste/b16_*.txt)
originals/MOONSHR (no patch at all) : in_race=False vbl=9129  $b2700 = 0   Bus Error reading at address $f00000, PC=$e21696 (48 lines)
build/mste_zero (zero patches)      : in_race=False vbl=9129  $b2700 = 0   Bus Error reading at address $f00000, PC=$e21696 (48 lines)
STE TOS 1.62 1 MB 16 MHz, default HD: in_race=True vbl=5809  MSPO
# TOS only: empty C:, no autorun (work/mste/tosonly.py MACHINE MEM TOS CLOCK SECS)
megaste 1024 TOS 2.06 clk  8: bus errors 0, $68d0 = 00 01
megaste 1024 TOS 2.06 clk 16: bus errors 1, $68d0 = 3f ee
megaste 2048 TOS 2.06 clk 16: bus errors 0, $68d0 = 00 01
megaste 4096 TOS 2.06 clk 16: bus errors 0, $68d0 = 00 01
megaste 1024 TOS 2.06 clk 16 --fast-boot no: bus errors 0 ; --cpu-exact false: bus errors 0
megaste 1024 TOS 2.06 clk  8 --video-timing ws1 / ws3 / ws4: bus errors 0, $68d0 = 00 01 (all three)
```
Screenshot `work/mste/tos_only_1m_16mhz.png` of the TOS-only 16 MHz boot: the Atari logo and **two bombs** (bomb count = exception number 2 = bus error), no game involved.
Mechanism (watch on `$68d0` with `--parse`, `work/mste/parse1.txt`, `regs.txt`): TOS 2.06 sets its video-mode variable `$68d0 = 1` at `$e15d4a` (A7 = `$6954`); at 16 MHz the next FDC-access call chain (`$e00d06 -> $e03d12 -> $e03fec`, read of `$ff8604`) runs with its stack 0x38 bytes lower (`ISP $68d2`, at 8 MHz `$690a`), and its return address `$00e03fee` is pushed over `$68d0-$68d1` (`$68d0 = 3fee`). Later `$e21672` scans a table until `cmp.w $68d0,d0` matches; `$68d0 = $3fee` never matches, the loop runs a0/a1 off the end of the ROM table to `$f00000` and bus errors (the instruction at `$e21694`, `move.w (a1)+,d0`). TOS 2.06's early-init stack shares its last 0x84 bytes with that variable, and the 16 MHz power-on phase (MFP interrupt storm during init, 1675 level-6 exceptions with `--trace cpu_exception`) nests deeper. `[INFERENCE]` for why the phase differs at 1 MB only (RAM size changes the memory-test time); the passes with `--cpu-exact false`, `--fast-boot no`, 2 MB, 4 MB, 8 MHz show it is a timing race. A real Mega STE powers up at 8 MHz and software raises it via `$ff8e21`; Hatari's `--cpuclock 16` at power-on is not that. **It is a Hatari/TOS issue independent of the game (the stock game bombs identically).**
Fix: `tools/play.sh` (and any launcher) boots at 8 MHz and raises the clock after TOS init (section 10.2).

### 10.2 `play.sh --cpu N`: boot at 8 MHz, then N MHz (Hatari `--parse`)
Mechanism tested (raw `work/mste/r_switch16.txt`): `hatari ... --cpuclock 8 --parse parse.txt`, `parse.txt` = `b VBL > 200 :trace :once :file clk.txt`, `clk.txt` = `setopt --cpuclock 16` (TOS init finishes at VBL 120 on this machine). Cold boot of build/mste_hd, Mega STE 1 MB: race reached (vbl 6048, MSPO); log line 18 `> setopt --cpuclock 16`; the extras counter of `mx_sync` (`$b8f38`, only counts above 8 MHz) `00 00 00 c8 -> 00 00 01 20` = 88 extra frames in 696 VBL in the race (`$1021 = 2`, `$100e = 407`).
```
RACE $1021 2 $100e 407 pos 3247 extras counter 000B8F38: 00 00 00 c8 -> 000B8F38: 00 00 01 20 over 696 VBL
```

### 10.3 TOS 2.06 1 MB layout: free RAM ends at `$E2BFF`, not `$E83FF`
Stock game (`originals/MOONSHR`), Mega STE TOS 2.06 1 MB 8 MHz, RAM dumps `work/dumps/ram_hook_1024_mste206.bin` (`pc = $b204e`), `ram_entry_1024_mste206.bin` (`pc = $6f64`), `ram_race0_1024_mste206.bin` (race, `msr.boot_to_race`), taken with `tools/msrhook.py --machine megaste --mem 1024 --tos 2.06` / `work/mste/racedump.py`. Registers at the hook instant equal the STE's (`A5=78000 A6=507AC A7=7FFF0 USP=B1F40`), so the hook, RUNME copy and `$B2700` are the same; the difference is at the top of RAM:
```
zero runs >= 8 KB at the hook instant:
STE 1.62  : $054000-$056000  $05fe00-$062000  $0b2700-$0e8400  $0fb700-$100000
Mega STE 2.06: $054000-$056000  $05fe00-$062000  $0b2700-$0e2c00  $0fb700-$100000
non-zero runs from $E2C50 (MSTE) / $E84D0 (STE): 'ATC_FPU', '8x8 system font', '8x16 system font', 'SCRENMGR', 'C:\RUNME.TOS', '#Z 00 C:\RUNME.TOS@' (desktop INF) ...
```
= live GEM/AES/desktop memory (fonts, resources, DESKTOP.INF) that TOS 2.06 allocates at `$E2C50-$F7FFF`; TOS 1.62 starts it at `$E84D0`. It is not inert: hook dump vs race dump differ in 7 bytes of it (`$e38f2-$e38f4`, `$e38ff-$e3901`: 1 1 7 -> 5 3 3, `$e6a3f`: 50 -> 186), so TOS writes there while the game runs. The old tool model (`FREE_END = $E8400`, `; ram:` checked only against the six STE 1.62 dumps) therefore let `rd_draw` (`$DB000-$E7FFF`) overlap the AES data on a 1 MB Mega STE (`$E2C50-$E7FFF`, about 21 KB). The old default build booted anyway at 8 MHz (above; the tables are written by `rd_init` and the AES data is not read by the game) but it was a real overlap, not a safe one. `[INFERENCE]`: whether a TOS-side write into the tables or a table write into AES data can crash a 1 MB Mega STE later (return to the desktop) was not exercised.

### 10.4 `rd_*` relocated, the tool model fixed, the final 1 MB map
**Size accounting (the lead asked where "14 KB" went): nothing went anywhere.** Before: `rd_geom` `$D0000-$DAFFF` = 45,056 B + `rd_draw` `$DB000-$E7FFF` = 53,248 B = 98,304 B = 96 KiB. After: `$C0000-$CAFFF` = 45,056 B + `$CB000-$D7FFF` = 53,248 B = 98,304 B. Both blocks moved down by exactly `$10000` (low 16 bits of every table address unchanged); only the `equ`s and the `; ram:` lines of `patches/rd_geom.s` / `rd_draw.s` changed (16 + 5 lines of constants/comments), no table content, size, layout or generation code. The unused tail of `rd_draw`'s block (`$E7044-$E7FFF` before, about 4 KB) and of `rd_geom`'s header (`$C0C60-$C0FFF`) were not reclaimed (they stay inside the declared ranges); the 96 KiB do not fit above `$BE000` together with A/B/C unless B's car cache is capped (below). In section 10.3 the statements "the AES data is not read by the game" and "the old build booted anyway" are `[INFERENCE]`/observation only: the boot passed, nothing proves the game never reads that region.
Tool (`tools/msrpatch.py`): `FREE_END = $E2C00` (was `$E8400`; the lower of the STE 1.62 and Mega STE 2.06 1 MB runs); `DUMPS_MSTE` = the three Mega STE 2.06 1 MB dumps added to `RAM_WITNESS` (every `; ram:` must be zero in them, in the six STE ones, and inside the free run of every layout); `check_free_run()` (called by `verify`): the whole free run `$B2800-$E2BFF` must be zero in every witness dump, so FREE_END cannot drift into TOS data; blob/`; data:` orgs above `$E2BFF` are refused through `BLOB_AREAS`. `test_blob36k` now declares `; conflicts: rd_geom` (its last image byte `$C16FF` lies in rd_geom's range). Negative controls (temporary patch dir, real `patches/` untouched; `work/mste/negctl.py`, raw `work/mste/negctl.txt`): `; ram:` `$E2000-$E3FFF` (straddles the ceiling), `$E8000-$E8FFF`, and the OLD rd_draw range `$DB000-$E7FFF` are each refused (`not free in the 1MB layout`, `not free in the 4MB layout`, `not zero in the stock game's RAM dump ram_hook_1024_mste206.bin` ...; `verify: 5 FAILED` / `11 FAILED`); `$E2000-$E2BFF` is accepted.
Final map (1 MB, all layouts; `list` shows `valid layouts for this set: 1MB, 4MB; free run(s) $b2800-$e2bff`):
```
$B2700-$BDFFF   payload image, default set 47,360 B (hd_*, mr_edge, rd blobs, mt/mx ...), site table $B7000
$BE000-$BEFFF   A (ta_*)                         4 KB   (free in the default set)
$BF000-$BFFFF   B (tb_*) data                    4 KB   ; $B3D00-$B67FF gaps of the payload: B ; $B6800-$B6FFF: C
$C0000-$CAFFF   rd_geom ram                      45,056 B
$CB000-$D7FFF   rd_draw ram                      53,248 B
$D8000-$E2BFF   free, 43,008 B: B's generated player-car cache $D8000-$DDFFF (24 KB cap set by the lead), $DE000-$E2BFF spare (19 KB)
$E2C00-         TOS 2.06 GEM/AES data (not ours)
```

### 10.5 `rd_*` gates re-run on the relocated build (offline, `work/mste/rd_offline.txt`; live images regenerated: `msrpatch.py live --only rd_geom --out work/road/live_geom`, `... rd_draw ... live_draw`; the `work/road/*.py` scripts retargeted to the new addresses)
```
geom_test.py live_geom 60       : frames 240 mismatching 0 | stock cycles mean 87429 | patched steady mean 47158 | first call (table generation) [903634, 891318, 891490, 891268]
geom_fuzz.py live_geom 2100 1   : fuzz 2100 cases, mismatches 0
geom_fuzz.py live_geom 200 1 neg: fuzz 200 cases, mismatches 31      (negative control: product table poisoned at $C1000: must differ)
geom_reuse_test.py live_geom    : standing frames 14 mismatches 0 cycles (full+save, reuse): [(903634, 12064), ...]
geom_sigtest.py live_geom       : sig tests 66 mismatches 0 wrongly taken reuse path (cycles<30k): 0
draw_test.py live_draw 60       : frames 240 mismatching 0 | stock mean 169085 | patched steady mean 95106 | first call [2037386]
draw_fuzz.py live_draw 900 1    : draw fuzz 900 streams, mismatches 0
draw_fuzz.py live_draw 100 1 neg: draw fuzz 100 streams, mismatches 31   (negative control: window table poisoned at $CB800: must differ)
```
Hatari A/B gates on the relocated tables (`work/mste/gates_ab.sh`, raw `work/mste/gates_ab.txt`; STE 1.62 1 MB snapshots, patches applied live; per-pass state `$1000-$13ff $29c8-$34ff $4500-$4fff $dae6` = 6,716 B per pass):
```
A: msrabtest --only rd_geom rd_draw rd_init --flips 10 40 --state 120
PIXELS race_grid/start/up/drive flips 10 and 40: IDENTICAL, md5 81dfec87 d5a188cf / 7481e0c7 7481e0c7 ; 3da506a7 c54efba9 / 90858e13 4858b4b8 ; 64f19a1d d9cdbe0a / 58491371 19ced56f ; d67d147e ed8944f1 / 3d3df84c 3d3df84c  (all equal to stock and to the pre-relocation md5s)
STATE race_grid  : common 117 passes, 785772 bytes compared, differing bytes 0
STATE race_start : common 124 passes, 832784 bytes compared, differing bytes 0
STATE race_up    : common 121 passes, 812636 bytes compared, differing bytes 0
STATE race_drive : common 122 passes, 819352 bytes compared, differing bytes 0
RESULT: ALL IDENTICAL
B (tick ON): msrabtest --only mr_edge mr_map mr_digit rd_geom rd_draw rd_init mt_clock mt_sync mt_pre --snapshots race_start race_drive --flips 10 --state 230
STATE race_start : common 233 passes, 1564828 bytes compared (6716 per pass), differing bytes 0
STATE race_drive : common 236 passes, 1584976 bytes compared (6716 per pass), differing bytes 0
RESULT: ALL IDENTICAL
C (negative control): --only rd_geom rd_draw mr_negctl --snapshots race_start --flips 10 : PIXELS DIFFER (1334 bytes of 64000)  RESULT: DIFFERENCES FOUND
```

### 10.6 Regression matrix on the final map (default HD build `build/mste_hd`, default floppy build `build/mste_floppy`, both rebuilt after the relocation: `verify: ALL OK`)
Every 68000 machine powers on at 8 MHz (`--cpuclock 8`), then the clock is raised after the boot (`h.set_cpuclock(16)`, the same switch `play.sh --cpu 16` does through `--parse`). HD: `work/mste/cold.py` (cold boot to the race, `$b2700` marker `MSPO`, hook sites, strip pixels == shadow render in both buffers (`work/hud/build/coldhd.py` checks), road tables, rate windows at 8 MHz and 16 MHz, then 124 s of driving: `$100e` advancing, `$1021 = 2`, RDG1 intact, log scan); raw `work/mste/m_hd.txt`. Floppy: `tools/msrfloppy.py gate ... --cpu 16`; raw `work/mste/m_floppy.txt`.
```
HD machine / TOS / RAM        boot_to_race  road tables (RDG1, WPTR == $135a)  8 MHz: passes/s, extras  16 MHz: passes/s, extras  124 s play        Bus Error lines
Mega STE 2.06 1 MB (the case) True vbl 6046  OK $c0000 / $d7040 = 000102ba     8.320, 110              8.333, 119                 alive, $1021=2     0
Mega STE 2.06 2 MB            True vbl 6047  OK                                8.347, 111              8.333, 123                 alive              0
Mega STE 2.06 4 MB            True vbl 6047  OK                                8.333, 110              8.320, 119                 alive              0
STE 1.62 1 MB                 True vbl 5809  OK                                10.076, 0               9.981, 184                 alive              1 (PP's $ff8e21 probe)
STE 1.62 4 MB                 True vbl 5809  OK                                9.981, 0                9.981, 185                 alive              1 (same)
ST 1.04 1 MB                  True vbl 5809  OK                                10.000, 0               10.000, 184                alive              2 (PP's $ff8e21 and $ff8924 probes; the stock game logs the same two: boot.py st 1024 1.04 originals/MOONSHR: Bus Error reading at address $ffff8924 / $ffff8e21, in_race=True vbl=5809)
TT 3.06 4 MB (native clock)   True vbl 5880  OK                                8.333, 525 (50 Hz window at 60 Hz VBLs)  -                       alive              0
Falcon 4.04 4 MB              True vbl 5802  OK                                10.000, 174             -                          alive              0
marker $b2700 = 4d 53 50 4f (MSPO) and `$ef7a = 4ef9000bb004`, `$edea = 4eb9000bb700` in every row; Mega STE 1 MB strip check: pixels != shadow render 0 in both buffers (a, b), shadow == model True; `$3cf0 = 0777`.
Mega STE 1 MB at 8 MHz "extras 110": the Mega STE 2.06 boots at native 60 Hz (VBL window 631 = 105 passes in 12.6 s), so the 10 passes/s pacer has slack even at 8 MHz; identical to the 2 MB/4 MB rows and to the earlier 4 MB-only result (hud_build.md: 8.333/s, extras 106).
Note on the `cold.py` line "old addresses $d0000 = ... $e7040 = ... (must be 0)": only `$e7040` means anything: STE and Mega STE 2/4 MB read 0 there; the 1 MB Mega STE reads `43dc0001` = TOS 2.06's own data (AES region, left untouched now; before the relocation `rd_draw` wrote WPTR there). `$d0000` now lies inside `rd_draw`'s window table A (nonzero by design).

FLOPPY gate (disk A alone, SPACE through the story screens, disk-2 swap, race; raised to 16 MHz after the race starts, 'up' held 40 s):
```
machine           disk-2 prompt  after swap (VBL, $1021/$100e)  marker  road magic / WPTR           extra frames/groups/ticks $b8f38 at 16 MHz
Mega STE 1 MB     True vbl 2900  4923, (2, 215)                  MSPO    RDG1 / 000102ba            0x2cf / 0x19b / 0x19d
Mega STE 4 MB     True vbl 2900  4922, (2, 216)                  MSPO    RDG1 / 000102ba            0x2b4 / 0x196 / 0x19b
STE 1.62 1 MB     True vbl 2408  4095, (2, 214)                  MSPO    RDG1 / 000102ba            0x25f / 0x199 / 0x19d
STE 1.62 4 MB     True vbl 2406  4093, (2, 215)                  MSPO    RDG1 / 000102ba            0x265 / 0x19b / 0x19d
ST 1.04 1 MB      True vbl 2408  4094, (2, 216)                  MSPO    RDG1 / 000102ba            0x264 / 0x19a / 0x19d
```
`play.sh --machine megaste --cpu 16` itself (the exact user command; Xvfb, 70 s): log line `> setopt --cpuclock 16`, 0 `Bus Error` lines (`work/mste/play_16.log`). `play.sh --machine megaste --print` and `--cpu 16 --print` print the command (with `--cpuclock 8 --parse build/play-clock/parse.txt` for 16) and build/copy nothing.
**Unproven:** (1) the Mega STE's external 16 KB cache is not emulated by Hatari 2.6.1 (`[INFERENCE]`, no run shows otherwise), so nothing here shows whether the generated/self-modified code (`rd_*` window tables are data; `mr_edge` slot code, payload written then executed after the trampoline) needs a flush on real Mega STE hardware; the trampoline's `cflush` is a no-op on a 68000 (delivery.md section 3); (2) real hardware; (3) whether the TOS 2.06 1 MB GEM data region could be read by the game after the race (return to desktop); the layout now avoids it. (4) Why exactly the 16 MHz power-on phase nests deeper at 1 MB only is `[INFERENCE]` (10.1). (5) TT/Falcon rows are native-clock, no 16 MHz switch.

## 11. Tightening integration (MSRTightIntegrate): the ta_*/tc_*/tb_car patches as defaults, gates, measured result
Machine: Hatari 2.6.1, headless harness (cycle-exact, `--fast-boot yes`), STE TOS 1.62 1 MB unless named. Scripts: `work/tint/` (`mxlib_int.py` builds every variant with the REAL `tools/msrpatch.py live` from its own default selection, so the gates test exactly what `build` ships; `exp_state_int.py`, `cmpstate_int.py`, `pix_int.py`, `steer_int.py`, `cyc` via `steer_int.py mode=cyc`, `cold_int.py`, `play5_int.py`, `ext_summary.py`, `cmp_cyc.py`, queues `run_q6.sh run_q7.sh run_q8.sh`); raw outputs `work/tint/res/`. `[INFERENCE]` marks what no output here proves. Nothing here touches `originals/`.

### 11.1 The default set, `list`, `verify`, sizes, the RAM map
Defaults flipped (`; default: yes` in the patch headers): `ta_erase ta_init ta_face ta_glyph ta_ymw`, `tc_clr tc_proj tc_dist tc_hit1 tc_hit2 tc_ord`, `tb_car tb_carph`; `hd_init` is now `default: no` (`ta_init` replaces it: declared `conflicts: hd_init` in `ta_init.s`; the tool refuses both together). Not default (documented as options): `ta_rb ta_rb0` (raster timing unproven on real hardware), `ta_nomouse` (behaviour risk, needs the user's approval), `ta_facestat` (visible), `tc_clrx`, `tb_blit tb_blit11 tb_blit13 tb_blit15` (not worth it), `hd_init`; `mx_*` stay default.
```
verify: ALL OK
fl_deprot          yes (floppy) disk A+$e3d0  (floppy disk patch, 4 B)
fl_hook            yes (floppy) disk A+$c350  (floppy disk patch, 10 B)
hd_clouds          yes      $07b3a     6 - / - / ram -
hd_nomap           yes      $0f9dc     4 - / - / ram -
hd_nomap2          yes      $120d6     6 - / - / ram -
hd_stage           yes      $0ef7a     6 $bb000,$bb800,$bc200,$bca40,$bcd00,$bcd20,$bd000 / $bcf00+160 / ram -
mr_edge            yes      $17c4a     6 $b3040 / - / ram -
mt_clock           yes      $0d128     6 $b8000 / $b8f00+4,$b8f08+4 / ram -
mt_pre             yes      $07b0a     6 $b8200 / - / ram -
mx_pre             yes      $07b46     6 $b8300 / $b9e00+2752 / ram -
mx_sync            yes      $07b74     6 $b8100,$b8380,$b8400 / $b8f04+4,$b8f20+224,$b9000+3584 / ram -
rd_draw            yes      $17c42     6 $b5000 / - / ram $cb000-$d7fff (rd_draw window tables (2 x 24 KB), colour table
rd_geom            yes      $100b4     6 $b4000 / - / ram $c0000-$cafff (rd_geom tables (magic, cached $1316, standing-f
rd_init            yes      $078f6     6 $b6000 / - / ram -
ta_erase           yes      $1209c     6 $be000 / $bef00+16 / ram -
ta_face            yes      $0f994     6 $be100 / - / ram -
ta_glyph           yes      $14fd4     6 $be600,$bec00,$be800 / - / ram -
ta_init            yes      $0edea     6 $be200 / - / ram -
ta_ymw             yes      $08e2c     6 $be400 / $bef40+16 / ram -
tb_car             yes      $039ac     4 $bf500 / $bf000+1280 / ram $d8000-$e2bff (generated player-car code cache (44,0
tb_carph           yes      $0ed90     8 $bfc00 / - / ram -
tc_clr             yes      $17c24     6 $b6d40 / $b6ff0+2 / ram -
tc_dist            yes      $0e2e8     6 $b6a00 / - / ram -
tc_hit1            yes      $18bf4     6 $b6a80 / - / ram -
tc_hit2            yes      $18c86     6 $b6b40 / - / ram -
tc_ord             yes      $0e406     8 $b6820 / - / ram -
tc_proj            yes      $0e316     8 $b6c00 / - / ram -
pp_bigram_cache    yes      HAGA+$3228  (file patch, 2 B)
hd_init            no       $0edea     6 $bb700 / - / ram -
ta_init            yes      $0edea     6 $be200 / - / ram -
tb_car             yes      $039ac     4 $bf500 / $bf000+1280 / ram $d8000-$e2bff (generated player-car code cache (44,032 B, written at run time))
tc_clr             yes      $17c24     6 $b6d40 / $b6ff0+2 / ram -
  hd_init            requires hd_stage
  ta_face            requires hd_stage ta_erase ta_init  conflicts ta_facestat
  ta_facestat        requires hd_stage ta_erase ta_init  conflicts ta_face
  ta_init            requires hd_stage ta_erase  conflicts hd_init
  tb_car             requires tb_carph
  tc_clr              conflicts tc_clrx
  $b6d40-$b6dd9    154 B  tc_clr       blob
  $b6ff0-$b6ff1      2 B  tc_clr       data
  $be200-$be21d     30 B  ta_init      blob
  $bf000-$bf4ff   1280 B  tb_car       data
  $bf500-$bf93b   1084 B  tb_car       blob
  $d8000-$e2bff  44032 B  tb_car       ram generated player-car code cache (44,032 B, written at run time)  [not in the image]
  valid layouts for this set: 1MB, 4MB; free run(s) $b2800-$e2bff
built /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/tight_hd with 25 patch(es) + 1 file patch(es); payload 54568 B at $b2700-$bfc27
floppy: disk A 819200 B, disk B 819200 B; payload 54568 B (107 sectors) at t0.0s2x9, t50.0s1x10, t51.0s1x10, t52.0s1x10...
```
Payload 47,360 B (HUD build) -> **54,568 B** (`$B2700-$BFC27`, 107 floppy sectors). RAM map at 1 MB (and 4 MB, TOS 2.06 1 MB ceiling `$E2BFF`): `$B6800-$B6FFF` tc_*, `$BE000-$BEFFF` ta_*, `$BF000-$BFFFF` tb_car/tb_carph, `$C0000-$CAFFF` rd_geom RAM, `$CB000-$D7FFF` rd_draw RAM, **`$D8000-$E2BFF` tb_car code cache = 44,032 B (0xAC00; the task text said 43,008 B, which is a miscount of the same range: `$E2C00 - $D8000 = $AC00`)**. `verify` ALL OK includes the whole-free-run zero check against the six STE 1.62 dumps and the three Mega STE 2.06 1 MB dumps and `; ram:` zero in all of them; `POOLEND` in `tb_car.s` is `$E2C00`. 4 MB layout: same addresses (`pp_bigram_cache` default).

### 11.2 Per-pass game state equal to stock (Hatari, `$7b86` after the flip, keyed by `$100e`; `m` counts DECIMAL: `$1000-$13ff` (1024) `$29c8` (2872) `$4500` (2816) `$dae6` (4) `$1bb0` (12) `$23bc` (16) `$27c8` (38) `$3500` (512) `$dafe` (4) `$6100` (24) `$b8f38` (12) = 7,334 bytes per pass)
A = stock game, T = the real default set with `mt_sync` (tick ON, no extras), X = the real default set (tick ON + extras). Stock vs T, race_start (driving, 220 passes asked) and race_drive (300 asked; the time-out and the restart are inside: keys 0..1706), mask = the documented HUD-private/display-scratch list, **`TC_GEOM` (road geometry output `$4724-$4f77`) NOT applied (`--nogeomask`)**:
```
res/st_start_A8.json (220 passes) vs res/st_start_T8.json (223): common 211 (keys 98..308); 1544942 bytes compared; mask=on (masked differing bytes 13666); differing addresses 0, differing bytes 0
   masked: 417 differing bytes in buffer parity/pointer $1004-$100d
   masked: 538 differing bytes in cloud counters $27de-$27ed (dd50 removed)
   masked: 10546 differing bytes in cloud slots $29c8-$2c67 (dd50 removed)
   masked: 625 differing bytes in dial cache $10d4-$10d7
   masked: 1039 differing bytes in minimap variables $10dc-$10e3
   masked: 140 differing bytes in position cache $10cc-$10cd
   masked: 1 differing bytes in position flag $11cc
   masked: 346 differing bytes in score cache/flag $11c4-$11c5 $11c7
   masked: 11 differing bytes in thermometer cache/flag $10bc-$10bd $11c9
   masked: 3 differing bytes in thermometer flag $11c9

res/st_drive_A8.json (306 passes) vs res/st_drive_T8.json (301): common 298 (keys 0..1706); 2181956 bytes compared; mask=on (masked differing bytes 21452); differing addresses 0, differing bytes 0
   masked: 1 differing bytes in IKBD mouse reply bytes $6106-$6117 (written by the ACIA interrupt, asynchronous to the pass)
   masked: 590 differing bytes in buffer parity/pointer $1004-$100d
   masked: 17624 differing bytes in cloud slots $29c8-$2c67 (dd50 removed)
   masked: 1138 differing bytes in dial cache $10d4-$10d7
   masked: 298 differing bytes in dial flag $11cd
   masked: 203 differing bytes in minimap variables $10dc-$10e3
   masked: 507 differing bytes in position cache $10cc-$10cd
   masked: 7 differing bytes in position flag $11cc
   masked: 542 differing bytes in score cache/flag $11c4-$11c5 $11c7
   masked: 53 differing bytes in score flag $11c7
   masked: 488 differing bytes in thermometer cache/flag $10bc-$10bd $11c9
   masked: 1 differing bytes in thermometer flag $11c9
```
Final mask set (all in `cmpstate_int.py`, each a named range with a per-category count of masked differing bytes printed): IKBD mouse reply bytes `$6106-$6117` (written by the ACIA interrupt, asynchronous to the pass: ONE byte differed once in race_drive pass key 0 without the mask: `$0610e 00 -> 03`; this range is new in this gate and was not in the earlier HUD gate), buffer parity/pointer `$1004-$100d`, raster scratch `$12f0-$1307`, raster bands `$12fe-$1301`, object order list scratch `$36e8-$36ff`, HUD kernel scratch `$100c-$100d`, the HUD caches/flags the removed old HUD items used to update (`$10bc-$10bd $11c9`, `$10c2-$10c9`, `$10cc-$10cd $11cc`, `$10d4-$10d7 $11cd`, `$10dc-$10e3`, `$11c4-$11c5 $11c7`, `$11ca-$11cb`, `$11da-$11dc`) and the cloud slots/counters `$29c8-$2c67`, `$27de-$27ed` (`dd50` removed with the clouds). **`TC_GEOM` is not needed with `tc_clr`** (the 'start'/'drive' blocks above); it is still needed in the extras gates, because an extra frame re-runs the road geometry at an extrapolated pose and the region holds the last extra's output at `$7b86` (below).

Extras at 16 and 32 MHz, same keys (`X` vs stock, mask + `TC_GEOM` as documented for the extras gates; the unmasked-by-TC_GEOM counts are printed to show that the ONLY other difference is that region):
```
-- start_A8 vs start_X16: with TC_GEOM:
res/st_start_A8.json (220 passes) vs res/st_start_X16.json (222): common 196 (keys 113..308); 1435112 bytes compared; mask=on (masked differing bytes 66258); differing addresses 0, differing bytes 0
   masked: 79 differing bytes in IKBD mouse reply bytes $6106-$6117 (written by the ACIA interrupt, asynchronous to the pass)
   masked: 52024 differing bytes in TC_GEOM (inherited display-scratch mask: road geometry output $4724-$4f77; NOT needed with tc_clr/rd_*: pass --nogeomask; needed only with tc_clrx = stale records below the stream start, see tighten_c.md section 5)
-- without TC_GEOM:
res/st_start_A8.json (220 passes) vs res/st_start_X16.json (222): common 196 (keys 113..308); 1435112 bytes compared; mask=on (masked differing bytes 14234); differing addresses 1362, differing bytes 52024
   $04724: 3 passes, e.g. pass 154: 00 -> ff
-- start_A8 vs start_X32: with TC_GEOM:
res/st_start_A8.json (220 passes) vs res/st_start_X32.json (223): common 197 (keys 112..308); 1442434 bytes compared; mask=on (masked differing bytes 75701); differing addresses 0, differing bytes 0
   masked: 61187 differing bytes in TC_GEOM (inherited display-scratch mask: road geometry output $4724-$4f77; NOT needed with tc_clr/rd_*: pass --nogeomask; needed only with tc_clrx = stale records below the stream start, see tighten_c.md section 5)
   masked: 787 differing bytes in buffer parity/pointer $1004-$100d
-- without TC_GEOM:
res/st_start_A8.json (220 passes) vs res/st_start_X32.json (223): common 197 (keys 112..308); 1442434 bytes compared; mask=on (masked differing bytes 14514); differing addresses 1385, differing bytes 61187
   $04724: 4 passes, e.g. pass 121: 00 -> ff
-- drive_A8 vs drive_X16: with TC_GEOM:
res/st_drive_A8.json (306 passes) vs res/st_drive_X16.json (305): common 285 (keys 0..1706); 2086770 bytes compared; mask=on (masked differing bytes 20662); differing addresses 0, differing bytes 0
   masked: 79 differing bytes in TC_GEOM (inherited display-scratch mask: road geometry output $4724-$4f77; NOT needed with tc_clr/rd_*: pass --nogeomask; needed only with tc_clrx = stale records below the stream start, see tighten_c.md section 5)
   masked: 564 differing bytes in buffer parity/pointer $1004-$100d
-- without TC_GEOM:
res/st_drive_A8.json (306 passes) vs res/st_drive_X16.json (305): common 285 (keys 0..1706); 2086770 bytes compared; mask=on (masked differing bytes 20583); differing addresses 79, differing bytes 79
   $04725: 1 passes, e.g. pass 1666: 21 -> 22
```
Extras counts in those windows (`$b8f38` over the recorded passes, from `res/state_log.txt`): X ste1m_race_start.sav 16 hits 222 extra frames in window 334;X ste1m_race_start.sav 32 hits 223 extra frames in window 888;X ste1m_race_drive.sav 16 hits 305 extra frames in window 0; The race_drive scene itself draws **0** extras at 16 MHz in those 300 passes (time-out and the standing start dominate: skip reasons, 11.6), so the steered gates below are the strong extras gate.

Steered state gates (input = a pure function of the pass key `$100e`, identical in every run: from key 140 (race_start) / 470 (race_up) 15 passes each of up, up+left, up, up+right; the player car changes bitmap constantly, so `tb_car` generates and uses code), mask as above, `TC_GEOM` only for X:
```
-- zig_start_A8 vs zig_start_T8: NOT RUN
-- zig_up_A8 vs zig_up_T8: NOT RUN
-- zig_start_A8 vs zig_start_X16: NOT RUN
-- zig_start_A8 vs zig_start_X32: NOT RUN
-- zig_up_A8 vs zig_up_X16: NOT RUN

```

### 11.3 Pixels
**(a) Full-buffer A/B** (`pix_int.py`: R = the HUD-build default `mr_edge rd_* hd_stage hd_init hd_clouds hd_nomap hd_nomap2`, C = the default set minus the pacer, both live-applied at the same instant, both 32,000-byte buffers, 7 render controls on the SAME capture; flips after the apply as listed; `$11ab` = ticker state). Summary over the captures, then the raw lines of the message-active captures:
`16` captures (race_start flips 10 55 90 100 150, race_grid 10 120 150, race_up 10 40 90 150, race_drive 10 40 90 150): **C identical to R in 16/16** (both buffers). Ticker message active (`$11ab != 0`): 7 captures. Negative controls (C + one poke), captures in which each control DIFFERS: car_nophase 1, erase_short 7, face_same 7, face_wrong 7, glyph_bad 6.
```
== race_start flip 55: $100e=170 $11ab=1 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   face_wrong   vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   erase_short  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   glyph_bad    vs R: differing pixels total   3032  (face box     0, text box  3032)  -> DIFFER
   car_nophase  vs R: differing pixels total     20  (face box     0, text box     0)  -> DIFFER
== race_start flip 90: $100e=205 $11ab=0 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_wrong   vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   erase_short  vs R: differing pixels total    642  (face box     0, text box   642)  -> DIFFER
   glyph_bad    vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   car_nophase  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
== race_start flip 150: $100e=265 $11ab=1 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   face_wrong   vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   erase_short  vs R: differing pixels total    484  (face box     0, text box   484)  -> DIFFER
   glyph_bad    vs R: differing pixels total   1322  (face box     0, text box  1322)  -> DIFFER
   car_nophase  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
== race_grid flip 10: $100e=3647 $11ab=1 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   face_wrong   vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   erase_short  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   glyph_bad    vs R: differing pixels total    581  (face box     0, text box   581)  -> DIFFER
   car_nophase  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
== race_up flip 90: $100e=512 $11ab=1 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   face_wrong   vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   erase_short  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   glyph_bad    vs R: differing pixels total   1184  (face box     0, text box  1184)  -> DIFFER
   car_nophase  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
== race_up flip 150: $100e=572 $11ab=1 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   face_wrong   vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   erase_short  vs R: differing pixels total    604  (face box     0, text box   604)  -> DIFFER
   glyph_bad    vs R: differing pixels total    119  (face box     0, text box   119)  -> DIFFER
   car_nophase  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
== race_drive flip 10: $100e=1696 $11ab=2 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   face_wrong   vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   erase_short  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   glyph_bad    vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   car_nophase  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
== race_drive flip 90: $100e=69 $11ab=2 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   face_wrong   vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   erase_short  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   glyph_bad    vs R: differing pixels total   2826  (face box    64, text box  2762)  -> DIFFER
   car_nophase  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
```
The controls: `face_same` (ta_face always 'same': `be112=600e`), `face_wrong` (draws sprite+1: `be11a=b0e4`), `erase_short` (`be042=0040`), `glyph_bad` (`be660=0002`), `car_nophase` (the `tb_carph` hook removed: `ed90=302a0006d06a0008`, i.e. the wheel-animation state is not tracked: the bank alternates and a stale compiled frame is drawn). `car_nophase` fires in 1 capture(s) only (the XOR toggles every other pass; the earlier tighten-B gate also saw it in a single capture); the three face/erase/glyph controls fire exactly where a message is on screen.

**(b) Masked gate against the real stock/HUD reference** (`tools/msrmask.py`, explicit rectangles, pixels compared AND excluded printed): cand = the default set, ref = `test_hdref hd_clouds mr_edge rd_*`, stock side = `mr_edge rd_*`, 4 scenes x flips 10 40 90 x both buffers = 24 frames (message active on several: `speech=Y` rows):
```
race_start  flip  40 b70000 (drawn=no ) speech=Y differing pixels A:0, B:0, C:0, D:0
race_start  flip  40 b78000 (drawn=yes) speech=Y differing pixels A:0, B:0, C:0, D:0
race_grid   flip  10 b70000 (drawn=yes) speech=Y differing pixels A:0, B:0, C:0, D:0
race_grid   flip  10 b78000 (drawn=no ) speech=Y differing pixels A:0, B:0, C:0, D:0
race_grid   flip  40 b70000 (drawn=yes) speech=Y differing pixels A:0, B:0, C:0, D:0
race_grid   flip  40 b78000 (drawn=no ) speech=Y differing pixels A:0, B:0, C:0, D:0
candidate: hd_stage ta_init ta_erase ta_face ta_glyph ta_ymw hd_clouds hd_nomap hd_nomap2 mr_edge rd_geom rd_draw rd_init tb_car tb_carph tc_clr tc_dist tc_hit1 tc_hit2 tc_ord
  A rows65-199 vs ref        frames   24  pixels compared    1036800  excluded         0  differing      0  -> IDENTICAL
  B sky rows16-64            frames   24  pixels compared     244608  excluded    131712  differing      0  -> IDENTICAL
  C strip rows0-15           frames   24  pixels compared     122880  excluded         0  differing      0  -> IDENTICAL
  D rows85-199 vs stock      frames   24  pixels compared     798336  excluded     84864  differing      0  -> IDENTICAL
RESULT: IDENTICAL
```
Negative controls (`--neg nopaint`: the first strip/sky paint is skipped, `--neg nowipe`: the sky wipe is skipped; each MUST differ):
```
-- res/mask_neg_nopaint.txt
candidate: hd_stage ta_init ta_erase ta_face ta_glyph ta_ymw hd_clouds hd_nomap hd_nomap2 mr_edge rd_geom rd_draw rd_init tb_car tb_carph tc_clr tc_dist tc_hit1 tc_hit2 tc_ord
  A rows65-199 vs ref        frames    2  pixels compared      86400  excluded         0  differing      0  -> IDENTICAL
  B sky rows16-64            frames    2  pixels compared      31360  excluded         0  differing   5902  -> DIFFER
  C strip rows0-15           frames    2  pixels compared      10240  excluded         0  differing   6668  -> DIFFER
  D rows85-199 vs stock      frames    2  pixels compared      66528  excluded      7072  differing      0  -> IDENTICAL
RESULT: DIFFER
-- res/mask_neg_nowipe.txt
candidate: hd_stage ta_init ta_erase ta_face ta_glyph ta_ymw hd_clouds hd_nomap hd_nomap2 mr_edge rd_geom rd_draw rd_init tb_car tb_carph tc_clr tc_dist tc_hit1 tc_hit2 tc_ord
  A rows65-199 vs ref        frames    2  pixels compared      86400  excluded         0  differing      0  -> IDENTICAL
  B sky rows16-64            frames    2  pixels compared      31360  excluded         0  differing   5032  -> DIFFER
  C strip rows0-15           frames    2  pixels compared      10240  excluded         0  differing      0  -> IDENTICAL
  D rows85-199 vs stock      frames    2  pixels compared      66528  excluded      7072  differing      0  -> IDENTICAL
RESULT: DIFFER
```

### 11.5 MEASURE: cycles per pass at 8 MHz, tick OFF (loop top `$796a` -> flip `$d1ca`, interrupts included; 1 VBL = 160,256 cycles; same Hatari session and recipe as `work/hud/build/res_cyc3.txt`)
Rows: N = the HUD-build default (`mr_edge rd_* hd_stage hd_init hd_clouds hd_nomap hd_nomap2`, re-measured now: the baseline), F = the new default minus the pacer (the cycle recipe needs the tick off). `speech` = `$11ab != 0` at the end of the pass (as in the earlier tables); both rows are matched on the same pass key `$100e` (same snapshot, same instant), so `delta` compares the same passes. race_start = driving (up held, no steering), race_grid = standing.
```
scene       passes         n   N cycles     VBL   F cycles     VBL      delta      VBL
race_start  no speech     83     491172   3.065     444497   2.774     -46675   -0.291
race_start  speech       146     517169   3.227     463676   2.893     -53493   -0.334
race_start  all          229     507747   3.168     456725   2.850     -51022   -0.318
race_grid   no speech     74     414960   2.589     362576   2.262     -52384   -0.327
race_grid   speech       158     417803   2.607     362531   2.262     -55272   -0.345
race_grid   all          232     416896   2.601     362546   2.262     -54350   -0.339
```
Unmatched window means (all passes of each 230-pass run, `res/cyc_log.txt`): N race_start none 8MHz no speech  n 83 mean 491172 = 3.065 VBL min 444540 max 552268 | N race_start none 8MHz speech     n 150 mean 516378 = 3.222 VBL min 444244 max 610324 |    all passes n 233 mean 507399 = 3.166 VBL; last 100 mean 517324 |    VBL per pass (end-to-end, incl. wait):  3.841 | F race_start none 8MHz no speech  n 88 mean 448449 = 2.798 VBL min 398460 max 529840 | F race_start none 8MHz speech     n 157 mean 467325 = 2.916 VBL min 392744 max 587452 |    all passes n 245 mean 460545 = 2.874 VBL; last 100 mean 475275 |    VBL per pass (end-to-end, incl. wait):  3.258 | N race_grid none 8MHz no speech  n 74 mean 414960 = 2.589 VBL min 394556 max 461460 | N race_grid none 8MHz speech     n 158 mean 417803 = 2.607 VBL min 400684 max 461344 |    all passes n 232 mean 416896 = 2.601 VBL; last 100 mean 415244 |    VBL per pass (end-to-end, incl. wait):  3.0 | F race_grid none 8MHz no speech  n 74 mean 362576 = 2.262 VBL min 342376 max 395512 | F race_grid none 8MHz speech     n 159 mean 362493 = 2.262 VBL min 342024 max 412640 |    all passes n 233 mean 362520 = 2.262 VBL; last 100 mean 361926 |    VBL per pass (end-to-end, incl. wait):  3.0 |

Per-agent savings overlap (shared stages): the sum of the three agents' stand-alone claims (A 7-20 k, B 39-42 k, C 7.3-9.2 k) is 53-71 k; the integrated, matched result is **-46.7 k / -53.5 k driving (no speech / speech) and -52.4 k / -55.3 k standing**.

**Steering and the pool (key-matched, 8 MHz, tick OFF, race_start, input = zig = up / up+left / up / up+right, 15 passes each from key 140; 520 passes; `steer_int.py mode=cyc zigk=140`).** N = HUD build, nocar = the default set minus `tb_car tb_carph`, pK = the default set with the `tb_car` pool limit poked (`cmpi.l #POOLEND,d0` immediate at `$BF772`) to `$D8000 + K KB`; compiled-draw fraction = executions of the generated-code hit path `$BF5E6` / executions of the stub `$BF500` (the stub is entered by every 4-column nibble-7 sprite, the car, its second layer and other objects; 'hits' also counts the draw right after a generation), counted by trace breakpoints in the same run:
```
variant                 mean cyc     VBL     vs nocar      vs N  compiled-draw fraction (hits / stub entries)
N (HUD build)             501791   3.131           +0        +0  -   (pool used up to $0, 0 entries)
default w/o tb_car        489249   3.053           +0    -13798  -   (pool used up to $0, 0 entries)
default, pool 8 KB        483975   3.020        -5274    -18815  328 / 1367 = 24.0 %   (pool used up to $d95, 29 entries)
default, pool 16 KB       477695   2.981       -11673    -25477  557 / 1316 = 42.3 %   (pool used up to $db8, 29 entries)
default, pool 24 KB       469829   2.932       -19420    -32953  733 / 1330 = 55.1 %   (pool used up to $dd7, 29 entries)
default, pool 32 KB       462171   2.884       -27078    -40522  967 / 1348 = 71.7 %   (pool used up to $df5, 29 entries)
default, pool 44 KB       459585   2.868       -29664    -43006  1057 / 1352 = 78.2 %   (pool used up to $e1d, 29 entries)
```
(`vs nocar` / `vs N`: mean over the matched passes of the 520-pass window, i.e. including the cold generation of every variant in the first ~100 passes; steady state from key +250 is 1-2 k better, see `res/pool_log.txt`.) The entry table (39 entries) never binds at 44 KB: 29 entries are used; an experimental 120-entry table (Unicorn census, `work/tightB/census.py`, not kept) changed the compiled fraction by -1..-2 points only, so the table was not enlarged. **Raising the pool from 24 KB to 44,032 B lifts the compiled-draw fraction from 55.1 % to 78.2 % under constant steering and saves a further 10.3 k cycles per pass (-0.064 VBL); against the 24 KB version's 47-68 % Unicorn estimate the Hatari measurement is 55 % at 24 KB** (the estimate was a model, this is the live count).

### 11.6 MEASURE: extra frames per tick (mx counters), tick ON (T=30), extras ON, STE, driving with steering
`steer_int.py mode=pass`: a persistent trace breakpoint at the race-pass top `$7a88` dumps, per pass, `NEXTRA $b8f32` (the extras drawn in the PREVIOUS pass's tick), the pass key, the counters `$b8f38/3c/40` (frames / ticks with >= 1 extra / ticks that entered the group code), the skip-reason words `$b8f54`, `$11ab`, `$1226`, `$1021`, the VBL; input = zig steering as a pure function of the key (up / up+left / up / up+right, 15 passes each, also after the restart). Scene race_drive: ~65 passes of the time-out sequence (`$1226 = 5`), the race restart (pass 1707 -> 0), 94 standing passes of the start sequence (skip reason 2 = standing), then racing. 1,300 passes = 6,500 VBL = 130 s emulated per run. Per-run raw: `res/ext_*.json`, summary `ext_summary.py`.
**Frames per tick = 1 main + extras. Racing phase only (after the restart, pass >= 130; the first lap of the new race):**
```
run                         ticks VBL/tick  pass/s  extras per tick histogram {extras: ticks}     mean ex. 2-frame disp fps
HUD build (NX) 8 MHz         1114    5.001   9.998  {0: 943, 1: 171}                                 0.154   15.4%    11.53
NEW default 8 MHz            1115    4.999  10.002  {0: 793, 1: 322}                                 0.289   28.9%    12.89
NEW default 16 MHz           1121    5.000  10.000  {0: 8, 1: 386, 2: 618, 3: 87, 4: 22}             1.758   34.4%    27.58
NEW default 32 MHz           1112    5.000  10.000  {0: 1, 1: 3, 2: 20, 3: 8, 4: 1080}               3.945    0.3%    49.45
```
`2-frame` = share of ticks with exactly one extra (main + 1 = 2 pictures); `disp fps` = (passes + extras) per second of the racing window (the game itself runs 10 logic steps per second in every row). With the tick ON the passes stay at 10.00/s in all rows, so the game speed is not affected by the extras.
Full-window view incl. the time-out sequence, the restart and the 94 standing passes (`ext_summary.py`; this is what an observer sees over 2 minutes):
```
== ext_X_8.json: set X 8 MHz, 1314 pass records over 6840 VBL (137 s @50Hz): 9.598 passes/s, 5.21 VBL/pass
   counters over the window: extra frames 349, ticks with >=1 extra (groups) 349, ticks that entered the group code 614; displayed fps (passes+extras)/time = 12.15
   extras per tick histogram (pass records): {0: 963, 1: 349}  -> frames per tick (main+extras): {1: '73.4%', 2: '26.6%'}
   mean extras/tick 0.266; ticks with >= 1 extra 26.6 %; with exactly 1 extra (2 frames) 26.6 %
   speech passes: n 1048 mean extras 0.247  hist {0: 789, 1: 259}
   no-speech passes: n 264 mean extras 0.341  hist {0: 174, 1: 90}
   restart at record 67 (pass 1707 -> 0, VBL 15378): extras of the passes around it [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]; $1226 around: [5, 5, 5, 5, 5, 0, 0]
   passes with $1226 != 0 (time-out sequence): 58; non-race mode ($1021 != 2) records 0
   skip reasons RSN (0 no slot copy, 1 off, 2 standing, 3 too fast, 4 $1024, 5 $1021) first/last: [11, 0, 0, 0, 0, 0] [615, 0, 94, 0, 0, 0]
== ext_X_16.json: set X 16 MHz, 1320 pass records over 6739 VBL (135 s @50Hz): 9.786 passes/s, 5.11 VBL/pass
   counters over the window: extra frames 2121, ticks with >=1 extra (groups) 1213, ticks that entered the group code 1220; displayed fps (passes+extras)/time = 25.52
   extras per tick histogram (pass records): {0: 105, 1: 436, 2: 668, 3: 87, 4: 22}  -> frames per tick (main+extras): {1: '8.0%', 2: '33.1%', 3: '50.7%', 4: '6.6%', 5: '1.7%'}
   mean extras/tick 1.609; ticks with >= 1 extra 92.0 %; with exactly 1 extra (2 frames) 33.1 %
   speech passes: n 1052 mean extras 1.589  hist {0: 83, 1: 364, 2: 527, 3: 58, 4: 20}
   no-speech passes: n 266 mean extras 1.688  hist {0: 22, 1: 72, 2: 141, 3: 29, 4: 2}
   restart at record 67 (pass 1707 -> 0, VBL 15378): extras of the passes around it [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]; $1226 around: [5, 5, 5, 5, 5, 0, 0]
   passes with $1226 != 0 (time-out sequence): 58; non-race mode ($1021 != 2) records 0
   skip reasons RSN (0 no slot copy, 1 off, 2 standing, 3 too fast, 4 $1024, 5 $1021) first/last: [1, 0, 0, 0, 0, 0] [5, 0, 94, 0, 0, 0]
== ext_X_32.json: set X 32 MHz, 1312 pass records over 6636 VBL (133 s @50Hz): 9.878 passes/s, 5.06 VBL/pass
   counters over the window: extra frames 4763, ticks with >=1 extra (groups) 1209, ticks that entered the group code 1216; displayed fps (passes+extras)/time = 45.77
   extras per tick histogram (pass records): {0: 101, 1: 6, 2: 24, 3: 8, 4: 1170, 5: 1}  -> frames per tick (main+extras): {1: '7.7%', 2: '0.5%', 3: '1.8%', 4: '0.6%', 5: '89.3%', 6: '0.1%'}
   mean extras/tick 3.636; ticks with >= 1 extra 92.3 %; with exactly 1 extra (2 frames) 0.5 %
   speech passes: n 1046 mean extras 3.630  hist {0: 79, 1: 6, 2: 23, 3: 8, 4: 929, 5: 1}
   no-speech passes: n 264 mean extras 3.659  hist {0: 22, 2: 1, 4: 241}
   restart at record 68 (pass 1707 -> 0, VBL 15377): extras of the passes around it [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]; $1226 around: [5, 5, 5, 5, 5, 0, 0]
   passes with $1226 != 0 (time-out sequence): 58; non-race mode ($1021 != 2) records 0
   skip reasons RSN (0 no slot copy, 1 off, 2 standing, 3 too fast, 4 $1024, 5 $1021) first/last: [2, 0, 0, 0, 0, 0] [2, 0, 94, 0, 0, 0]
== ext_NX_8.json: set NX 8 MHz, 1313 pass records over 6837 VBL (137 s @50Hz): 9.595 passes/s, 5.21 VBL/pass
   counters over the window: extra frames 183, ticks with >=1 extra (groups) 183, ticks that entered the group code 409; displayed fps (passes+extras)/time = 10.93
   extras per tick histogram (pass records): {0: 1128, 1: 183}  -> frames per tick (main+extras): {1: '86.0%', 2: '14.0%'}
   mean extras/tick 0.140; ticks with >= 1 extra 14.0 %; with exactly 1 extra (2 frames) 14.0 %
   speech passes: n 1047 mean extras 0.127  hist {0: 914, 1: 133}
   no-speech passes: n 264 mean extras 0.189  hist {0: 214, 1: 50}
   restart at record 67 (pass 1707 -> 0, VBL 15378): extras of the passes around it [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]; $1226 around: [5, 5, 5, 5, 5, 0, 0]
   passes with $1226 != 0 (time-out sequence): 58; non-race mode ($1021 != 2) records 0
   skip reasons RSN (0 no slot copy, 1 off, 2 standing, 3 too fast, 4 $1024, 5 $1021) first/last: [17, 0, 0, 0, 0, 0] [825, 0, 94, 0, 0, 0]
```
- X_8: ticker active (`$11ab != 0`, 926 ticks) mean 0.267 extras, ticker idle (189 ticks) 0.397.
- X_16: ticker active (`$11ab != 0`, 930 ticks) mean 1.724 extras, ticker idle (191 ticks) 1.927.
- X_32: ticker active (`$11ab != 0`, 923 ticks) mean 3.940 extras, ticker idle (189 ticks) 3.968.
Other scenes at 8 MHz (steered, 700 passes, `res/ext8_*.json`; the amount of spare time depends on the scene: objects, speech):
```

```
Time-out restart: no extras during the time-out sequence (skip reason 5 / `$1024 != 0`) and none in the standing start sequence (skip reason 2 = standing, 94 passes), both unchanged by the tightening; the extras resume when the car moves. In the full-window summaries above the lines `restart at record ...` show the extras of the 20 passes around the restart: all 0.

**Reading for the STE at 8 MHz [measured above, the interpretation is an INFERENCE]:** after the tightening the pass costs ~2.8-2.9 VBL of a 5-VBL tick, but an extra frame needs the whole road/object path again (about the same cost minus the logic stage and the HUD work), so only part of the ticks have room for one: the new default draws one extra picture in about 29 % of the racing ticks (the HUD-build default: 15 %), ~12.9 displayed fps instead of 11.5; it can never draw two. The deadline rule (`wantnext`) only starts an extra when it is predicted to flip before the next tick; 79 of the 349 extra-drawing ticks in the 137-s window still ended one or two VBL late (the next tick is then shortened: passes per second stay 10.00), see the VBL histogram: `VBL between pass starts: 3 x3, 4 x77, 5 x1153, 6 x76, 7 x3` (`res/ext_X_8.json`).

### 11.7 Cold boots, floppy, 5-minute plays, native 60 Hz
HD: `work/tint/cold_int.py` (cold boot of `build/tight_hd` = the default HD build, SPACE navigation into the first race, marker `$b2700`, patched sites, HUD strip pixels == shadow render in both buffers, road tables `RDG1`/`WPTR`, `tb_car` probe byte `INIT $bf000` (1 = generated path on, 2 = stock kernel), `tc_clr` flag `$b6ff0`, then rate windows at the native clock and at 16 MHz (68000 machines boot at 8 MHz and the clock is raised after the boot, as `play.sh --cpu 16` does), `up` held, then 124 s of play; `$ff820a` read for the refresh rate). Raw `res/cold_hd.txt`:
```
=== HD cold ste 1024 1.62 0,16
ste 1024 KB TOS 1.62 build build/tight_hd: boot_to_race True vbl 5811
marker $b2700: b'MSPO' stage site $ef7a: 4ef9000bb004 $edea: 4eb9000be200 palette A col 14 $3cf0: 0000
STRIP CHECK cold_tint_ste_1024_a pass>=86: $100e=86 $11ab=2 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 2743 (raw), shadow==model(RAM) True | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 2743 (message/face excluded? no: raw), shadow==model(RAM) True
STRIP CHECK cold_tint_ste_1024_b pass>=397: $100e=397 $11ab=1 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1750 (raw), shadow==model(RAM) False | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1793 (message/face excluded? no: raw), shadow==model(RAM) True
TB_CAR INIT $bf000 = 1 (1 generated path on, 2 off) NENT $bf008 = 8 POOLP $bf004 = 000db052  TC_CLR flag $b6ff0 = 0100  sites: $17c24 4ef9000b6d40 $e406 4ef9000b68204e71 $39ac 000bf500
RESULT ste 1024 TOS 1.62 clock native: window 526 VBL, passes 105 (9.981/s @50Hz), extra frames 0, displayed fps 9.981, $ff820a=fe00, pos 3677->4474
RESULT ste 1024 TOS 1.62 clock 16: window 525 VBL, passes 105 (10.000/s @50Hz), extra frames 174, displayed fps 26.571, $ff820a=fe00, pos 4967->5690
PLAY DONE: 124 s at 16 MHz, $1021=2, magic b'RDG1', Bus/Address Error lines in the log: 2, hatari alive: True
TB_CAR at end: INIT 1 NENT 2 POOLP 000d904a
=== HD cold ste 4096 1.62 0,16
ste 4096 KB TOS 1.62 build build/tight_hd: boot_to_race True vbl 5810
marker $b2700: b'MSPO' stage site $ef7a: 4ef9000bb004 $edea: 4eb9000be200 palette A col 14 $3cf0: 0000
STRIP CHECK cold_tint_ste_4096_a pass>=88: $100e=88 $11ab=2 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 2743 (raw), shadow==model(RAM) True | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 2743 (message/face excluded? no: raw), shadow==model(RAM) True
STRIP CHECK cold_tint_ste_4096_b pass>=399: $100e=399 $11ab=1 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1868 (raw), shadow==model(RAM) False | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1901 (message/face excluded? no: raw), shadow==model(RAM) True
TB_CAR INIT $bf000 = 1 (1 generated path on, 2 off) NENT $bf008 = 8 POOLP $bf004 = 000db052  TC_CLR flag $b6ff0 = 0100  sites: $17c24 4ef9000b6d40 $e406 4ef9000b68204e71 $39ac 000bf500
RESULT ste 4096 TOS 1.62 clock native: window 526 VBL, passes 105 (9.981/s @50Hz), extra frames 0, displayed fps 9.981, $ff820a=fe00, pos 3677->4474
RESULT ste 4096 TOS 1.62 clock 16: window 525 VBL, passes 105 (10.000/s @50Hz), extra frames 173, displayed fps 26.476, $ff820a=fe00, pos 4974->5697
PLAY DONE: 124 s at 16 MHz, $1021=2, magic b'RDG1', Bus/Address Error lines in the log: 2, hatari alive: True
TB_CAR at end: INIT 1 NENT 2 POOLP 000d9046
=== HD cold megaste 1024 2.06 0,16
megaste 1024 KB TOS 2.06 build build/tight_hd: boot_to_race True vbl 6047
marker $b2700: b'MSPO' stage site $ef7a: 4ef9000bb004 $edea: 4eb9000be200 palette A col 14 $3cf0: 0000
STRIP CHECK cold_tint_megaste_1024_a pass>=110: $100e=110 $11ab=0 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 0 (raw), shadow==model(RAM) True | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 0 (message/face excluded? no: raw), shadow==model(RAM) True
STRIP CHECK cold_tint_megaste_1024_b pass>=421: $100e=421 $11ab=1 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1626 (raw), shadow==model(RAM) True | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1675 (message/face excluded? no: raw), shadow==model(RAM) True
TB_CAR INIT $bf000 = 2 (1 generated path on, 2 off) NENT $bf008 = 0 POOLP $bf004 = 00000000  TC_CLR flag $b6ff0 = 0100  sites: $17c24 4ef9000b6d40 $e406 4ef9000b68204e71 $39ac 000bf500
RESULT megaste 1024 TOS 2.06 clock native: window 630 VBL, passes 105 (10.000/s @60Hz), extra frames 116, displayed fps 21.048, $ff820a=fc00, pos 3677->4474
RESULT megaste 1024 TOS 2.06 clock 16: window 630 VBL, passes 105 (10.000/s @60Hz), extra frames 112, displayed fps 20.667, $ff820a=fc00, pos 4967->5690
PLAY DONE: 124 s at 16 MHz, $1021=2, magic b'RDG1', Bus/Address Error lines in the log: 0, hatari alive: True
TB_CAR at end: INIT 2 NENT 0 POOLP 00000000
=== HD cold megaste 2048 2.06 0,16
megaste 2048 KB TOS 2.06 build build/tight_hd: boot_to_race True vbl 6046
marker $b2700: b'MSPO' stage site $ef7a: 4ef9000bb004 $edea: 4eb9000be200 palette A col 14 $3cf0: 0000
STRIP CHECK cold_tint_megaste_2048_a pass>=111: $100e=111 $11ab=0 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 0 (raw), shadow==model(RAM) True | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 0 (message/face excluded? no: raw), shadow==model(RAM) True
STRIP CHECK cold_tint_megaste_2048_b pass>=422: $100e=422 $11ab=1 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1841 (raw), shadow==model(RAM) True | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1817 (message/face excluded? no: raw), shadow==model(RAM) True
TB_CAR INIT $bf000 = 2 (1 generated path on, 2 off) NENT $bf008 = 0 POOLP $bf004 = 00000000  TC_CLR flag $b6ff0 = 0100  sites: $17c24 4ef9000b6d40 $e406 4ef9000b68204e71 $39ac 000bf500
RESULT megaste 2048 TOS 2.06 clock native: window 630 VBL, passes 105 (10.000/s @60Hz), extra frames 115, displayed fps 20.952, $ff820a=fc00, pos 3670->4467
RESULT megaste 2048 TOS 2.06 clock 16: window 630 VBL, passes 106 (10.095/s @60Hz), extra frames 112, displayed fps 20.762, $ff820a=fc00, pos 4960->5690
PLAY DONE: 124 s at 16 MHz, $1021=2, magic b'RDG1', Bus/Address Error lines in the log: 0, hatari alive: True
TB_CAR at end: INIT 2 NENT 0 POOLP 00000000
=== HD cold megaste 4096 2.06 0,16
megaste 4096 KB TOS 2.06 build build/tight_hd: boot_to_race True vbl 6047
marker $b2700: b'MSPO' stage site $ef7a: 4ef9000bb004 $edea: 4eb9000be200 palette A col 14 $3cf0: 0000
STRIP CHECK cold_tint_megaste_4096_a pass>=111: $100e=111 $11ab=0 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 0 (raw), shadow==model(RAM) True | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 0 (message/face excluded? no: raw), shadow==model(RAM) True
STRIP CHECK cold_tint_megaste_4096_b pass>=422: $100e=422 $11ab=1 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1675 (raw), shadow==model(RAM) True | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1699 (message/face excluded? no: raw), shadow==model(RAM) True
TB_CAR INIT $bf000 = 2 (1 generated path on, 2 off) NENT $bf008 = 0 POOLP $bf004 = 00000000  TC_CLR flag $b6ff0 = 0100  sites: $17c24 4ef9000b6d40 $e406 4ef9000b68204e71 $39ac 000bf500
RESULT megaste 4096 TOS 2.06 clock native: window 630 VBL, passes 105 (10.000/s @60Hz), extra frames 115, displayed fps 20.952, $ff820a=fc00, pos 3677->4474
RESULT megaste 4096 TOS 2.06 clock 16: window 630 VBL, passes 105 (10.000/s @60Hz), extra frames 111, displayed fps 20.571, $ff820a=fc00, pos 4967->5697
PLAY DONE: 124 s at 16 MHz, $1021=2, magic b'RDG1', Bus/Address Error lines in the log: 0, hatari alive: True
TB_CAR at end: INIT 2 NENT 0 POOLP 00000000
=== HD cold st 1024 1.04 0,16
st 1024 KB TOS 1.04 build build/tight_hd: boot_to_race True vbl 5808
marker $b2700: b'MSPO' stage site $ef7a: 4ef9000bb004 $edea: 4eb9000be200 palette A col 14 $3cf0: 0000
STRIP CHECK cold_tint_st_1024_a pass>=86: $100e=86 $11ab=2 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 2743 (raw), shadow==model(RAM) True | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 2743 (message/face excluded? no: raw), shadow==model(RAM) True
STRIP CHECK cold_tint_st_1024_b pass>=397: $100e=397 $11ab=1 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1750 (raw), shadow==model(RAM) False | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1793 (message/face excluded? no: raw), shadow==model(RAM) True
TB_CAR INIT $bf000 = 1 (1 generated path on, 2 off) NENT $bf008 = 8 POOLP $bf004 = 000db052  TC_CLR flag $b6ff0 = 0100  sites: $17c24 4ef9000b6d40 $e406 4ef9000b68204e71 $39ac 000bf500
RESULT st 1024 TOS 1.04 clock native: window 526 VBL, passes 105 (9.981/s @50Hz), extra frames 0, displayed fps 9.981, $ff820a=fe00, pos 3677->4474
RESULT st 1024 TOS 1.04 clock 16: window 526 VBL, passes 105 (9.981/s @50Hz), extra frames 174, displayed fps 26.521, $ff820a=fe00, pos 4967->5690
PLAY DONE: 124 s at 16 MHz, $1021=2, magic b'RDG1', Bus/Address Error lines in the log: 3, hatari alive: True
TB_CAR at end: INIT 1 NENT 2 POOLP 000d904a
=== HD cold tt 4096 3.06 0
tt 4096 KB TOS 3.06 build build/tight_hd: boot_to_race True vbl 5879
marker $b2700: b'MSPO' stage site $ef7a: 4ef9000bb004 $edea: 4eb9000be200 palette A col 14 $3cf0: 0000
STRIP CHECK cold_tint_tt_4096_a pass>=129: $100e=129 $11ab=0 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 0 (raw), shadow==model(RAM) True | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 0 (message/face excluded? no: raw), shadow==model(RAM) True
STRIP CHECK cold_tint_tt_4096_b pass>=439: $100e=439 $11ab=1 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1974 (raw), shadow==model(RAM) True | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1974 (message/face excluded? no: raw), shadow==model(RAM) True
TB_CAR INIT $bf000 = 2 (1 generated path on, 2 off) NENT $bf008 = 0 POOLP $bf004 = 00000000  TC_CLR flag $b6ff0 = 0100  sites: $17c24 4ef9000b6d40 $e406 4ef9000b68204e71 $39ac 000bf500
RESULT tt 4096 TOS 3.06 clock native: window 630 VBL, passes 105 (10.000/s @60Hz), extra frames 526, displayed fps 60.095, $ff820a=0100, pos 3677->4474
PLAY DONE: 124 s at native MHz, $1021=2, magic b'RDG1', Bus/Address Error lines in the log: 0, hatari alive: True
TB_CAR at end: INIT 2 NENT 0 POOLP 00000000
=== HD cold falcon 4096 4.04 0
falcon 4096 KB TOS 4.04 build build/tight_hd: boot_to_race True vbl 5806
marker $b2700: b'MSPO' stage site $ef7a: 4ef9000bb004 $edea: 4eb9000be200 palette A col 14 $3cf0: 0000
STRIP CHECK cold_tint_falcon_4096_a pass>=116: $100e=116 $11ab=0 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 0 (raw), shadow==model(RAM) True | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 0 (message/face excluded? no: raw), shadow==model(RAM) True
STRIP CHECK cold_tint_falcon_4096_b pass>=426: $100e=426 $11ab=1 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1964 (raw), shadow==model(RAM) True | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1964 (message/face excluded? no: raw), shadow==model(RAM) True
TB_CAR INIT $bf000 = 2 (1 generated path on, 2 off) NENT $bf008 = 0 POOLP $bf004 = 00000000  TC_CLR flag $b6ff0 = 0100  sites: $17c24 4ef9000b6d40 $e406 4ef9000b68204e71 $39ac 000bf500
RESULT falcon 4096 TOS 4.04 clock native: window 526 VBL, passes 105 (9.981/s @50Hz), extra frames 181, displayed fps 27.186, $ff820a=0200, pos 3677->4467
PLAY DONE: 124 s at native MHz, $1021=2, magic b'RDG1', Bus/Address Error lines in the log: 0, hatari alive: True
TB_CAR at end: INIT 2 NENT 0 POOLP 00000000
```
All eight machines boot to the race with marker `MSPO`, the new sites patched (`$17c24 -> $b6d40`, `$e406 -> $b6820`, `$39ac -> $bf500`), road tables intact, `$1021 = 2` after 124 s of play, and 0 Bus/Address Error lines on Mega STE/TT/Falcon (2-3 on ST/STE are PP's `$ff8e21`/`$ff8924` probes, as in the stock game, `integration.md` 10.6). **`tb_car` probe: `INIT = 1` (generated path ON) on STE 1.62 1 MB/4 MB and ST 1.04; `INIT = 2` (stock kernel) on Mega STE 2.06 (1/2/4 MB), TT 3.06 and Falcon 4.04, exactly the declared rule.** STRIP CHECK lines (the HUD pixel/shadow check) are identical to the HUD-build default's (`mste/m_hd.txt`: e.g. `non-sky pixels rows 16-64 2743` / `1750`/`1793`, the 'shadow==model False' flag at pass 397 appears in the HUD-build run as well, a timing artefact of the check) = the render with all patches equals the earlier default's. At the native 8 MHz clock the STE windows show 0 extras (the first lap right after the start light: ticker message active, objects, start sequence: no room), the 16 MHz windows 173-174 extras in 105 passes (26.5 fps); the 60 Hz boots (Mega STE 2.06 `$ff820a = fc`, TT 3.06 `$ff820a = 01`) run 10.000 passes per second at 60 Hz; the Mega STE draws 112-116 extras in 105 passes, the TT 526 (60 fps displayed).

Floppy (`tools/msrfloppy.py gate build/tight_floppy/disk_a.st --disk-b build/tight_floppy/disk_b.st`, disk A alone, story screens, disk-2 swap, race, clock raised to 16 MHz, `up` held; raw `res/cold_floppy.txt`):
```
=== FLOPPY gate megaste 1024 2.06 16
disk-2 prompt True t 46 vbl 2901 story screen seen True screens saved 7 in /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/shots/floppy_tint_megaste_1024
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
after swap: vbl 4925 $1021/$100e (2, 215)
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
road magic $c0000: 000C0000: 52 44 47 31 00 0a 00 00                          RDG1....  WPTR $d7040: 000D7040: 00 01 02 ba                                      ...´
extra-frame counters at 16 MHz, up held, $100e 692: frames/groups/ticks $b8f38: 000B8F38: 00 00 02 d6 00 00 01 99 00 00 01 9d              ...ש...Ö...¥  skip reasons $b8f54: 000B8F64: 00 00                                         
=== FLOPPY gate megaste 4096 2.06 16
disk-2 prompt True t 46 vbl 2900 story screen seen True screens saved 7 in /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/shots/floppy_tint_megaste_4096
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
after swap: vbl 4923 $1021/$100e (2, 216)
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
road magic $c0000: 000C0000: 52 44 47 31 00 0a 00 00                          RDG1....  WPTR $d7040: 000D7040: 00 01 02 ba                                      ...´
extra-frame counters at 16 MHz, up held, $100e 693: frames/groups/ticks $b8f38: 000B8F38: 00 00 02 d8 00 00 01 9a 00 00 01 9d              ...ן...Ü...¥  skip reasons $b8f54: 000B8F64: 00 00                                         
=== FLOPPY gate ste 1024 1.62 16
disk-2 prompt True t 46 vbl 2409 story screen seen True screens saved 6 in /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/shots/floppy_tint_ste_1024
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
after swap: vbl 4096 $1021/$100e (2, 217)
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
road magic $c0000: 000C0000: 52 44 47 31 00 0a 00 00                          RDG1....  WPTR $d7040: 000D7040: 00 01 02 ba                                      ...´
extra-frame counters at 16 MHz, up held, $100e 695: frames/groups/ticks $b8f38: 000B8F38: 00 00 02 89 00 00 01 9b 00 00 01 9e              ...ë...¢...ß  skip reasons $b8f54: 000B8F64: 00 00                                         
=== FLOPPY gate ste 4096 1.62 16
disk-2 prompt True t 46 vbl 2408 story screen seen True screens saved 6 in /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/shots/floppy_tint_ste_4096
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
after swap: vbl 4095 $1021/$100e (2, 215)
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
road magic $c0000: 000C0000: 52 44 47 31 00 0a 00 00                          RDG1....  WPTR $d7040: 000D7040: 00 01 02 ba                                      ...´
extra-frame counters at 16 MHz, up held, $100e 693: frames/groups/ticks $b8f38: 000B8F38: 00 00 02 8c 00 00 01 9b 00 00 01 9d              ...î...¢...¥  skip reasons $b8f54: 000B8F64: 00 00                                         
=== FLOPPY gate st 1024 1.04 16
disk-2 prompt True t 46 vbl 2407 story screen seen True screens saved 6 in /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/shots/floppy_tint_st_1024
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
after swap: vbl 4094 $1021/$100e (2, 216)
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
road magic $c0000: 000C0000: 52 44 47 31 00 0a 00 00                          RDG1....  WPTR $d7040: 000D7040: 00 01 02 ba                                      ...´
extra-frame counters at 16 MHz, up held, $100e 693: frames/groups/ticks $b8f38: 000B8F38: 00 00 02 8e 00 00 01 9a 00 00 01 9d              ...Ä...Ü...¥  skip reasons $b8f54: 000B8F64: 00 00
```

5-minute plays, default HD build, STE 1.62 1 MB (`work/tint/play5_int.py`: cold boot, SPACE, `up` held plus a wall-clock left/right toggle every 6 s, 16,700 VBL = 334 s, samples every 10 s, a screenshot 6 s after each restart; the 8 MHz run is the native clock, the 16 MHz run switches the clock after the boot). Raw `res/play5_8.txt`, `res/play5_16.txt`; screenshots `work/tint/shots/play5_ste_1024_{8,16}_after_restart1.png` (HUD strip, message and face, road, car and objects intact after the restart: viewed):
```
-- play5_8
in_race True vbl 5809
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
RESTART seen: pass 1707 -> 0 at VBL 8779
shot after restart taken
extras (frames, groups, ticks) at start (0, 0, 0) at end (1078, 1078, 1868) -> extra frames 1078 in 17117 VBL
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....  CLK/NEXT/PEND: 000B8F00: 00 01 a6 c4 00 01 a6 dc 00 00 00 00              ..ªג..ªץ....
alive, fc advancing: 1698
road $c0000: 000C0000: 52 44 47 31 00 0a 00 00                          RDG1.... WPTR: 000D7040: 00 01 02 ba                                      ...´ restarts 1 tb_car INIT/NENT/POOLP 000BF000: 01 00 06 ab 00 0e 19 80 00 1d 02 a0              ...½...Ç...á
(261, 2, 79, 0, (3, 3, 11), 4) (vbl, mode, pass, $1226, extras (frames, groups, ticks), NENT)
(3265, 2, 680, 0, (185, 185, 348), 21) (vbl, mode, pass, $1226, extras (frames, groups, ticks), NENT)
(6270, 2, 1281, 0, (383, 383, 654), 25) (vbl, mode, pass, $1226, extras (frames, groups, ticks), NENT)
(9325, 2, 129, 0, (540, 540, 948), 9) (vbl, mode, pass, $1226, extras (frames, groups, ticks), NENT)
(12330, 2, 730, 0, (720, 720, 1301), 22) (vbl, mode, pass, $1226, extras (frames, groups, ticks), NENT)
(15334, 2, 1331, 0, (949, 949, 1643), 26) (vbl, mode, pass, $1226, extras (frames, groups, ticks), NENT)
-- play5_16
in_race True vbl 5810
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
RESTART seen: pass 1696 -> 29 at VBL 8629
shot after restart taken
extras (frames, groups, ticks) at start (0, 0, 0) at end (5666, 3191, 3198) -> extra frames 5666 in 17117 VBL
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....  CLK/NEXT/PEND: 000B8F00: 00 01 a8 0e 00 01 a8 1a 00 00 00 00              ..¿...¿.....
alive, fc advancing: 20
road $c0000: 000C0000: 52 44 47 31 00 0a 00 00                          RDG1.... WPTR: 000D7040: 00 01 02 ba                                      ...´ restarts 1 tb_car INIT/NENT/POOLP 000BF000: 01 00 00 2a 00 0d 90 46 00 02 00 30              ...*..ÉF...0
(261, 2, 112, 0, (84, 55, 58), 4) (vbl, mode, pass, $1226, extras (frames, groups, ticks), NENT)
(3265, 2, 713, 0, (1144, 657, 659), 23) (vbl, mode, pass, $1226, extras (frames, groups, ticks), NENT)
(6270, 2, 1314, 0, (2259, 1257, 1260), 24) (vbl, mode, pass, $1226, extras (frames, groups, ticks), NENT)
(9325, 2, 189, 0, (3036, 1731, 1736), 11) (vbl, mode, pass, $1226, extras (frames, groups, ticks), NENT)
(12330, 2, 790, 0, (4077, 2332, 2337), 25) (vbl, mode, pass, $1226, extras (frames, groups, ticks), NENT)
(15334, 2, 1390, 0, (5210, 2933, 2938), 26) (vbl, mode, pass, $1226, extras (frames, groups, ticks), NENT)
```

### 11.8 Not done / unproven / for the user
- **Steered state gates (zig) and the other-scene 8 MHz extras runs (race_start/race_up) were NOT completed** (queued `run_q7.sh`, `run_q8.sh`, stopped for time; the rows above say NOT RUN). The state evidence for `tb_car` with a constantly changing bitmap is therefore: the tighten-B gates (8/8, incl. extras at 8/16/32 MHz and race_drive restart), the pixel gate here (16/16 identical, steering input in the race_up/race_drive snapshots is the snapshot's), and the 5-minute plays (steered by wall clock, 1 restart, no crash); NOT a per-pass state gate under steering on the integrated build. Re-run: `work/tint/run_q7.sh` (waits for `res/all.done`: `touch` it).
- race_drive extras gate at 16 MHz saw 0 completed extras (time-out/standing dominate); the extras state gate is carried by race_start X16/X32 (334 / 888 extras).
- Hatari only; no real hardware; the Mega STE cache is not emulated (tb_car is off there by rule). `ta_rb*`, `ta_nomouse`, `ta_facestat`, `tc_clrx`, `tb_blit*` stay options.
- The 8 MHz extras statement 'draws none' in older notes is superseded: measured 15 % of ticks (HUD build) and 29 % (new default) in the race_drive scene; 0 in the first lap right after the start light (cold windows).
- Decision for the user: none blocking. Optional: ta_nomouse (-8.3 k/pass), ta_rb/rb0 (-4.5 k) would take driving to about 2.7 VBL.
