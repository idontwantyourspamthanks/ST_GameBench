# The grey palette fade on every load (PP's loader service) and `pp_nofade`

Evidence: Hatari 2.6.1, tools/mw2harness.py, disassembly of `work/dumps/ram_ingame_lobos.bin` (2 MB dump; the
service lives at $1F8000..) with `tools/m68dis.py`; all addresses below are written `HB+$xxxx` = offset in the file
`HAGA` = RAM `$1F8000+xxxx` on 2 MB and `$F8000+xxxx` on 1 MB (so `HB+$1166` = $1F9166 / $F9166). Everything not
marked [INFERENCE] was read from disassembly or a run.

## 1. Where the code is: HAGA, not RUNME.TOS

The brief assumed the service is part of RUNME's relocated image. It is not:

```
fade routine head (24 B) 45fa0e1e34f8824034f8825e50d23a3c07003c3c00703e3c
  HAGA (13448 B)                 : 1 hit, file offset $1166
  work/dumps/RUNME_unpacked.tos  : 0 hits      RUNME.TOS (shipped, 4122 B) : 0 hits
  ram_ingame_lobos.bin           : 1 hit, $1F9166   (= $1F8000 + $1166)
```
HAGA is copied verbatim to `phystop-$8000` (the `[$462]` pointer of loading.md: `$F8000` on 1 MB, `$1F8000` on 2 MB).
Only its runtime-written bytes differ from the file (292 bytes: header words $80-$B3, saved vectors/palettes at
$14A8.., `$1F8A` flag, ...; code is identical). The file's first words are an entry table:
`$100 $402 $616 $864 $fc4 $1806 $1962 $27fc $2976 $29f8 $2aec $2c42 $2e9a $3122 $327e $16ac`
(`$fc4` = the file service the game calls through `jsr ([$462]+[$8008])`, `$16ac` = Fsfirst/Fsnext service,
`$1806` = exit to desktop, `$1962` = savestate entry [INFERENCE from the code it reaches]).
=> a patch cannot be at a fixed RAM address and need not be in RUNME: it is an edit of the HAGA file
(`patches/pp_nofade.s`, tool extension "file patches").

## 2. The fade machinery (HAGA offsets; raw listing from the dump)

Service entry `HB+$0fc4` (every Fopen/Fseek/Fread/Fwrite/Fclose the game does, also `'Wr'` writes of FFD):
```
0fc4 copy 28-byte request {buf,seek,len,mode,name} to HB+$3360        (lea.l HB+$3360(pc),a1 ; 7 x move.l)
0fd4 tst.b HB+$00af -> bne $15ba    (TT/Falcon "hard disk" path: no swap, no fade: jsr (a1) into TOS)
0fe0 move sr,-(a1) ; move #$2700,sr ; movem.l d2-d7/a2-a7,-(a1) ; move usp ; usp=HB+$37a4 ; a7=HB+$3614
0ff8 bsr.w HB+$17be     save+clear the MFP enable regs ($fa07-$fa0d..), only VBL stays
0ffc bsr.w HB+$1166     <== FADE TO GREY + swap in TOS low memory
1000 ... trap #1  Fopen($3d) / Fseek($42) / Fread($3f)|Fwrite($40) in <=2 pieces / Fclose($3e) at $1020..$111e
1120 addq.l #4,a7 ; 1122 move #$2700,sr
1126 bsr.w HB+$1372     <== swap out TOS low memory + FADE BACK
112a restore MFP regs, regs from HB+$337c, wait ACIA empty, move (a1)+,sr, rts   ($1164)
```
Fade to grey, `HB+$1166` .. `$1276`, then the swap-in tail `$1278` .. `$1370` (listing in the tool output of `m68dis`):
```
1166 lea HB+$1f86(pc),a2 ; move.w $8240.w,(a2)+ ; move.w $825e.w,(a2)+ ; st.b (a2)     save pal 0 and 15, FLAG HB+$1f8a = $ff
1174 d5=$700 d6=$70 d7=$7 ; 1180 clr HB+$14ae..$14b3 (3 word sums)
1188 sum R,G,B nibbles of the 16 palette words ($8240..); 11ac..11d6 target grey = (3*R+2*G+B)/$c0 repeated in R,G,B
11d8 move.l $70.w,HB+$14a8 ; $70 = HB+$12a2 ; move #$2300,sr
     HB+$12a2 is `rte` (4e73): the "VBL handler" does nothing, it only lets `stop` wake up
11ec d3=6 ; loop:                                            -- up to 7 iterations
11f2   stop #$2300 ; stop #$2300                              2 VBL per iteration
11fa   for each of the 16 palette entries: save the entry in HB+$14b8+32*k (the palette BEFORE this step),
       step every R,G,B level by one toward the grey target, write it back ($8240+2i), count entries at target
1258   cmpi #16,count ; beq out ; dbra d3                    out after k iterations (k <= 7 because levels are 0..7)
1264 d4 = 6 - d3 ; HB+$14ac = d4                             step count (0..6): fade-back slots
126e move #$2700,sr ; move.l HB+$14a8(pc),$70.w ; swap in:   $1278 d1 = HB+$0083 (machine type 5/4/else) ...
     $12da..$1370 swap the TOS low memory ($8.. , 12 longs per round) with the game copy [HB+$0094], then `move #$2300,sr ; rts`
```
Fade back, entered by `bsr HB+$1372` after the I/O (`1372..145e` is the matching swap-out, same structure as the swap-in),
then, merging at `HB+$1460`:
```
1460 move.l $70.w,HB+$14a8 ; $70 = HB+$12a2 (rte) ; move #$2300,sr
1474 d1 = HB+$14ac (steps) ; a1 = HB+$14b8 + 32*(d1+1)
1484 loop: stop #$2300 ; stop #$2300 ; write 16 words from the saved slots, last slot first, to $8240..$825e ; dbra d1
149c move #$2700,sr ; move.l HB+$14a8(pc),$70.w ; rts
```
The last slot written is slot 0 = the palette as read at the first step, so the original palette comes back exactly
(measured, section 4).

### Callers (full list; byte-pattern + disassembly search of the whole HAGA)
| routine | caller (HAGA offset) | path |
|---|---|---|
| fade to grey `$1166` | `$0ffc` | file service (`$0fc4`) |
| | `$16d8` | Fsfirst/Fsnext service (`$16ac`) |
| | `$1b74` | savestate / exit-to-desktop path (entry `$1962` reaches it via `$1b26`: saves CPU, MFP, palette state [INFERENCE: that is the savestate / exit-to-desktop feature]; then sets $8240=$666 $825e=$116 and draws text on the live screen) |
| swap out + fade back `$1372` | `$1126` | file service |
| | `$173e` | Fsfirst/Fsnext service |
| | `$1f1e` and `$1f16` | savestate resume / exit to desktop |

## 3. When it fires, and why a transition has so many cycles

Once per service call, i.e. per call of `HB+$0fc4` / `HB+$16ac`. A call is one Fopen+Fseek+Fread(len $30D40=200000)+Fclose of
the chunk cache (loading.md 1.2: `$200` stub, `[$466]` request), made only when the game's sector read misses the cached
200 KB window of the current image; so it fires per Fread *chunk*, not per file and not per seek of the game. The window
holds one range only: the directory sectors (seek 0, re-read for every file) and a data window at seek >= $31800 evict
each other, hence the 0 / x / 0 / y pattern below. One screen change loads ~20 files and needs 8-10 chunks.

Observed corridor -> Personnel (1 MB STE snapshot `1mb_mode_select`; the I/O is identical with and without the patch):
`pc = $F9000` (service, after the fade call) hit 8-10 times (request block copied to `$FB360`: buf=$81000 every time, len 200000,
mode 0, name FFB) and `$278de` (game file setup) 21 times:

```
seek 0x000000  0x031800  0x000000  0x033c00  0x06e400  0x06c000  0x000000  0x05d600   (FFB, len 200000) + 2 more
loads: files 2 3 0 4 5 6 7 8 9 .. -> dest $40040.. $5638a, then file $6b -> $68000
```
Each call = fade to grey (<= 7 steps x 2 `stop`s = 2 VBL each) + fade back (same), i.e. up to 28 VBL per call by the code.
Measured with `e VBL` at every `$F9000` / `$2794a` hit, first to last hit of the transition (same 27 hits both runs):
original **349 VBL (7.0 s at 50 Hz)**, patched **173 VBL (3.5 s)** (`/tmp/lf/snap7_*`, snapshot run; per-hit deltas e.g. 24 22 27 17 35 vs
12 10 16 4 23). The rest of the 3.5 s is the game's own fade in/out and real disk time. In the original the gaps between calls also show
the washed-out grey frames (screenshots every 0.5 s, `/tmp/lf/snap10_orig.png`: grey corridor/boss frames) that the patch removes.
PP's README.TXT: "saves from game may take little more time too, while screen fades to gray and back multiple time": the same service
(`'Wr'` writes of the FFD campaign disk included).

Palette-write counts with `b ($ff8242).w ! ($ff8242).w :trace` over the corridor -> Personnel click on a cold-booted 1 MB
Mega ST (TOS 1.04), the lead's method, with the PC of each hit logged (`:file` + `r`):

| build | changes | by PC |
|---|---|---|
| original | **235** (an earlier run of the same: 222; the lead: 234) | game `$27244` x6, `$2729c` x2; service `$F9190` x5, `$F9206` x37, `$F9208` x44, `$F921E` x44, `$F9234` x43, `$F924C` x46, `$F9494` x8 |
| + pp_nofade | **8** | game `$27244` x6, `$2729c` x2 only |

(`$F9206..$F9234` are the `move.w (a2),dN` READS of the step loop; the watch also fires on the value Hatari returns for
$ff8242 read-back changing; `$F924C` is the compare after the write and `$F9494` the fade-back write. The count is a proxy for
"how much the service touches the palette"; the 8 left are PP's/the game's own palette setup of the new screen.)

## 4. Decision: (a) disable the fade completely, because the service never touches the visible screen

Evidence that the loads do not overwrite what is displayed (patched run, snapshot `1mb_mode_select`, breakpoints at
`$278de` (file setup), `$F9000` (service after the fade call), `$2794a` (file loaded), each dumping `$ff8200`, `$ff8240`):

* video base at every one of the 20+ hits: `$ff8200 = 00 07 00 00 00 07 00 52` = displayed screen `$070000` ($7D00 bytes);
* service request `buf` = `$81000` in all 10 calls (the 200 KB chunk cache, `$81000-$B1D40`), never video RAM;
* game copy destinations `[$6918]` of the 21 loads: `$040040 $042832 $049c20 $04b99e $04cb1a $04d3f8 $04d660 $04e078 $04e6b8 $04fc26
  $0507c0 $052116 $052cba $0532e4 $055b7e $055f84 $05638a`, last file `$6b` (6069 B) -> `$068000..$0697B5`: all outside both screen
  buffers ($60000-$67D00, $70000-$77D00);
* the palette at every hit is the full corridor palette (`0000 0100 0200 0300 0110 0221 0332 0443 0210 0321 0532 0111 0222 0640 0650 0777`),
  i.e. the fade is not what hides anything: the game copies the data to its destination between service calls, with the palette
  already faded back.
* screenshots every 0.3 s over the transition (80 frames): corridor, the game's own fade out/in, Personnel; no garbage frame
  (contact sheet made from the run, not kept; raw hit logs: work/notes/load_fade_evidence.txt).

So the fade is a pure "disk access" indicator (and a delay), (b) fade once per burst is not needed.

Exactness of the original restore (original code, snapshot, `$ff8240..$825f` dumped at `$F9166` entry and `$F94A6` exit of each of the 8 calls,
raw): every pair identical

```
00FF8240: 00 00 01 00 02 00 03 00 01 10 02 21 03 32 04 43
00FF8250: 02 10 03 21 05 32 01 11 02 22 06 40 06 50 07 77      (8 x at entry, 8 x at exit)
```

## 5. The patch (`patches/pp_nofade.s`, file patch on HAGA, 56 bytes in 4 edits)

Both service callers jump over the fade: `bsr.w HB+$1166` -> `bsr.w HB+$1278` (the swap-in tail; `SR` is already `$2700`, nothing
after `$1278` uses a register the skipped code set). Consequences: no fade, no save of $8240/$825e, **no `st.b` of the flag
`HB+$1f8a`**. That flag is read/cleared only by the savestate path (`lea HB+$1f86(pc)` at `$1166`, `$1bd0`, `$1f22`: whole disassembly),
so after the change `HB+$1f8a != 0` exactly while the savestate path runs (its entry `$1b74` still calls `$1166`).
The shared fade-back (`HB+$1460`) now returns at once (`rts` at `$14a6`, SR=$2700 as the old exit left it, $70 untouched) when
`HB+$1f8a` is zero, otherwise runs the old loop. To fit the extra test in the 36 bytes the old head used, the saved `$70` is kept
on the stack instead of `HB+$14a8` and `a1` is computed with `lea HB+$14d8(pc,d0.w),a1` (`d0 = d1<<5`).
Net: the savestate path is unchanged (still fades), the file/Fsfirst service paths do not touch the palette, no new code space,
no change to RUNME.TOS, 1 MB and 2 MB identical bytes (the tool assembles with `HB=$1F8000` and `HB=$F8000` and compares).

```
0ffc 61000168 -> 6100027a        16d8 6100fa8c -> 6100fb9e
1460 (36 B) -> move.b HB+$1f8a(pc),d0 ; beq.s $14a6 ; move.l $70.w,-(a7) ; lea HB+$12a2(pc),a2 ; move.l a2,$70.w
               move.w HB+$14ac(pc),d1 ; move.w d1,d0 ; lsl.w #5,d0 ; lea HB+$14d8(pc,d0.w),a1 ; move #$2300,sr ; nop
149c (12 B) -> move #$2700,sr ; move.l (a7)+,$70.w ; nop ; rts
```

Tool: `tools/mw2patch.py` file patches (`; image: HAGA`, `; edit: <offset> <orig hex>`, `org HB+$<offset>`), verified against the shipped
HAGA and the RAM dump, rejected if not position independent, applied to the build copy only. `build` without the patch is byte-identical to
before (whole tree `diff -r`, RUNME.TOS md5 52cf2bbdd28ffd8fe4682f1b9894d723).

## 6. Not covered
* TT/Falcon take `HB+$15ba` (no fade at all); not touched.
* The savestate/exit-to-desktop fade is kept on purpose; the savestate path itself was not exercised. The shared fade-back with the
  flag set (the code the savestate path runs) was: see test 5.

## 7. Tests (raw numbers in work/notes/load_fade_evidence.txt)

Builds: `python3 tools/mw2patch.py build --only <the 19 default patches> pp_nofade --out build/nofade` (`pp_nofade` is `default: no`).

1. **T1, corridor -> Personnel palette-change count** (lead's method: cold boot to M/J/K, press M, `b ($ff8242).w ! ($ff8242).w :trace`,
   goto(554,105), click):
   | machine | original | build/nofade |
   |---|---|---|
   | Mega ST, TOS 1.04, 1 MB | 235 (222 in an earlier run) | **8** (all game `$27244`/`$2729c`) |
   | STE, TOS 1.62, 2 MB | not measured cold | **4** (all game `$27244`) |
   | STE snapshot `1mb_mode_select`, 1 MB | 20 (16 service + 4 game) | 4 |
   Final palette after the transition is the same on original and patched Mega ST
   (`01 21 03 10 04 21 05 32 06 43 07 54 01 24 04 24 05 55 04 44 04 00 07 63 02 31 02 10 00 00 07 77`).
2. **T2, screenshots** corridor -> Personnel -> Use This Agent -> corridor -> Control map (-> boss intro, Lobos, briefing, objectives, boss, 3D)
   on both machines: every frame is a correct screen; the only intermediate frames are the game's own fades and the map being drawn
   progressively, which the ORIGINAL shows as well (snapshot run, screenshots every 0.5 s). The original additionally shows washed-out grey
   frames during its loads; they are gone.
3. **T3, full cold boot with the 19 defaults + pp_nofade**: both `MWPO` (`$B2FF8 = 4d 57 50 4f`), `$6220=d $700a=2` (3D view), walking
   (long at `$66e6`: `0x6400 -> 0x5db2` Mega / `0x5db7` STE in 12 s) and a turn (`$6742` `0x300 -> 0x2c6`) work on Mega ST 1 MB TOS 1.04 and
   STE 2 MB TOS 1.62.
   **Harness finding**: with the patch the literal `boot_to_game('M')` misses the `?` click on the objectives page (5 of 5 runs at the
   harness's timing: 4 cold boots + 1 snapshot), then the thumbs-up click lands on nothing and it ends `$6220=0`. Loads are twice as fast, so
   the objectives slideshow reaches its page change (which loads files) around the harness's blind `sleep(15)`; [INFERENCE] the click is lost
   because it arrives during that load (the service drains the ACIA on exit, `HB+$1154`..`$1160`; not verified by a trace). The same click
   works at other phases (snapshot, patched: after 6 s, 12 s, 17 s of waiting all hit on the first try; original: after 30 s). One retry
   fixes it (used in the runs above, which then reached the 3D view):
   ```python
   bossref = GAME_DIR/"work"/"ref"/"boss_thumbs.png"            # exact match at screenshot box (590, 60, 740, 125)
   self.goto(140,415); self.click(); time.sleep(6)
   for _ in range(6):
       if self.screen_matches(bossref, (590,60,740,125)): break
       self.goto(140,415); self.click(hold=0.8); time.sleep(6)
   ```
   (tools/mw2harness.py was not changed.)
4. **T4**: `python3 tools/mw2patch.py verify` -> `verify: ALL OK`. `build` with the default set, old tool (copy of the tool before the change) vs new
   tool, same patch dir minus `pp_nofade.s`: whole output tree identical (`diff -rq`), RUNME.TOS md5 52cf2bbdd28ffd8fe4682f1b9894d723 with the
   19 defaults of the test builds and cf6ed481e554a8251b55cd80851f849d after another agent made the `p4_hud_*` patches default; HAGA unchanged.
   Negative tests of the tool: a wrong
   `orig` -> `MISMATCH`, `verify` fails; an absolute-address segment -> `not position independent (203c001f9278 at $1F8000 vs 203c000f9278 at $F8000)`.
5. **Rewritten fade-back, flag set** (snapshot, flag `$F9F8A = $FF` as left by the original code, only the two fade-back edits applied, fade-to-grey
   still original): 8 service calls, 8 fade-back writes at `$F9494`, `$ff8240..$825f` identical at entry/exit of every call, transition completes.
6. Timing: first to last load event of corridor -> Personnel 349 VBL original, 173 VBL patched (section 3).
