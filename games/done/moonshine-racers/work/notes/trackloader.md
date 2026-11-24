# Moonshine Racers: stage 2 (the in-game track loader), research and recommended design (MSRLoaderStudy, 2026-11-20)

Study only: nothing under `patches/`, `tools/`, `dist/`, `build/`, `originals/` was changed (the shipped default build was rebuilt into `/tmp` and compared, see 1.2). Scratch scripts, logs and snapshots: `work/trackloader/`.
Machine for every Hatari run: Hatari 2.6.1-devel (`~/Code/AtariST/hattari/build/src/hatari`), private `HOME=/tmp/msrl_home`, own scratch dirs, one Hatari at a time. Game = the SHIPPED v1.0 HD build (`dist/MoonshineRacers_hd_v1.0.zip`, unzipped to `/tmp/msrl_dist/MOONSHR`; byte-identical to a fresh `msrpatch.py build` of the current source: `cmp` of HAGA, RUNME.TOS, PATCHES.TXT = same).
Tags: **[obs]** raw tool output kept in `work/trackloader/` (file named); **[disasm]** `tools/m68dis.py` on `work/dumps/ram_race_start.bin` (stock game, race) and on the patched-build dumps in `work/trackloader/snap/`; **[INFERENCE]** not proven.
Companion of `work/notes/trackeditor.md` (the viability study, "the study" below).

## 0. Result in one page

| # | question | answer |
|---|---|---|
| 1 | 4 MB cold boot of the patched HD build | **Works** (STE TOS 1.62 4 MB and 2 MB, Mega STE TOS 2.06 4 MB and 2 MB: all four reach a real race, `$23c0 != 0`, `$100e > 30`). The study's failure was **a stale `build/hd`**: its HAGA is the unpatched original (`pp_bigram_cache` missing: `HAGA+$3228 = 2412`, not `602a`), so at 4 MB the whole-image disk cache overwrites the payload and the game crashes (payload area read back all zero, bus errors). The shipped zip is fine. A second trap: `boot_to_race()` already returns True on the TITLE screen (`$1021 = 2` there). Section 1. |
| 2 | free RAM, patched build, race | `$100000-$1CD7FF` is zero and untouched at 2 MB (Mega STE; `$1D87FF` on an STE), `$100000-$1F4FFF` at 4 MB; HAGA/TOS-copy addresses **measured** at 2 MB (HAGA `$1F8000`, TOS copy `$1CD8BC` / `$1D89B4`). Section 2. |
| 3 | finish/win rule | **Found and proven**: the race ends when the player gets within 500 units of the ONE object whose sprite index is `$21` (the BAR, one per level, 15 of 15 tracks); `race length` (`$57890`) is not the finish. Any finishing place wins (tested at place 10). Section 3. |
| 4 | redirect design | Two RAM sites suffice and are verified in the patched build's RAM; plus one wrapper site `$72c4` that makes **every per-level table follow the BASE level automatically** by swapping `$102c := base[pos]` for the duration of the race. **Proven live** in a restored race (section 4.4). |
| 5 | campaign disk read path | **Works** on the HD build at >= 2 MB through the HAGA TOS window: `Fopen/Fread` of `MSTRACKS.TRK` (122,892 B) from `C:\FILES` in **0.7 s**, from a FAT12 floppy image in drive A in **16 s** (Hatari FDC timing), byte-identical, race keeps running, IKBD parser idle afterwards. Floppy build: feasible only with another code path (own FDC driver, no HAGA); recommend HD-only for v1.1. Section 5. |
| 6 | `rd_geom` standing reuse | Key = 33 words (`sigtab`), includes `$102c` and the six stream pointers; cheapest invalidation = `clr.b $C0008.l` (`SIGOK`) once per race setup. Section 6. |

Recommended stage-2 design: section 7. Costs and risks: section 8. File list for the lead: section 9.

## 1. The 4 MB cold boot (question 1)

### 1.1 Result
Recipe (`work/trackloader/boot_snap.py`, built on `tools/msr.py`): `boot_to_race()`, then SPACE every 6 s until the race loop really runs (`$23c0 != 0` = track stream pointer set, `$100e > 30`). Game = the shipped HD build.
```
machine / TOS / RAM        race reached (VBL)   $2dc (HAGA)  $42e (phystop)  HAGA+$83 type  HAGA+$3228   log
STE 1.62 4 MB              6681                 $3f8000      $400000         2 (STE)        602a         boot_ste_4096.txt
STE 1.62 2 MB              6682                 $1f8000      $200000         2              602a         boot_ste_2048.txt
Mega STE 2.06 4 MB         7089                 $3f8000      $400000         3 (Mega STE)   602a         boot_megaste_4096.txt
Mega STE 2.06 2 MB         7094                 $1f8000      $200000         3              602a         boot_megaste_2048.txt
(each: RESULT in_race = True ... $102c 0 $5ff8 0 $130c 0; $23c0 = $58c14; HAGA signatures +$17be/+$1166/+$1372 = 4dfa1c04 / 45fa0e1e / 123aed0f)
```
[obs] Raw: `work/trackloader/boot_*.txt`, dumps `snap/*.bin`, memstates `snap/*.sav`. The machine-type byte HAGA+`$83` is **3 on the Mega STE** (the study said "STE = 2" only).

### 1.2 What was wrong in the study (section 7.5 of trackeditor.md)
1. **`build/hd` is stale.** [obs] `md5 build/hd/HAGA = b34607ed...` = the ORIGINAL HAGA (`originals/MOONSHR/HAGA`), `HAGA+$3228 = 24 12` (unpatched `move.l (a2),d2`), `RUNME.TOS = 12a69cf9...`; the shipped zip has `HAGA = 59083376...` (`+$3228 = 60 2a`, the `pp_bigram_cache` edit; `cmp -l` shows exactly the two bytes `12841/12842`) and `RUNME.TOS = 22aa2d76...`. A fresh `python3 tools/msrpatch.py build --out /tmp/msrl_build/hd` reproduces the zip byte for byte (HAGA, RUNME.TOS, PATCHES.TXT `cmp` equal). `build/hd` (written 2026-11-17 17:34) predates the zip (2026-11-18 01:30) and is not the release. [INFERENCE: why `build/hd` lacks the HAGA edit although its PATCHES.TXT lists it; not investigated, not needed.]
2. **Mechanism of the failure, reproduced** (`boot_stale.py build/hd 4096`, `boot_stale_hd_4m.txt`): after 170 s `boot_to_race = False`, `$b2700` (payload marker `MSPO`) reads **all zero** (the 4 MB whole-image mode reads MS1 over `$81000-$C6F2B`, over the payload; `delivery.md` section 5), `$42e` = 0, `$1021 = 0`, `WARN : Bus Error reading at address $a5409f94, PC=$a5409f94` (9 times), HAGA record `+$3228 = 24 12`. The `$100e` "cycling" of the study is the intro before the crash.
3. **`boot_to_race()` is not a race test.** It returns True as soon as `$1021 == 2`, which already holds on the title screen ("Hi, I'm Ike's cousin, Billy Joe": `snap/ste2m_hd.png`). `tools/msr_boot_test.py` therefore prints `in_race = True` for the shipped build at 4 MB at VBL 5809 (`boot_ste4m.txt`) while only the title is up. `run_race.py` of the study already knew this ("SPACE until `$23c0 != 0 and $100e > 30`"); `boot_snap.py` does the same for every machine. No change to the shipped tool is needed for the release; stage-2 gates must use the `$23c0`/`$100e` test.

## 2. Free RAM in the patched build during a race (question 2)

Method: cold boot of the shipped build, `savebin` of all RAM at the standing start (`snap/*.bin`), `zeromap.py` (512-byte granularity, runs >= 4 KB, same method as the study's `msrdump`). The TOS-state buffers of HAGA were located by searching for the live low-RAM image (`$400..`) in the dump. [obs] files `snap/*.zeromap.txt`.
```
                     phystop  HAGA base  TOS copy (image of addr 8)  free run (zero in the race)                        non-zero above it
STE 1.62   2 MB     $200000  $1F8000    $1D89B4                     $0D9200-$1D87FF  (1021 KB)                         $1D8800-$1D9DFF, $1DB000-$1FB7FF (TOS copy + HAGA)
Mega STE   2 MB     $200000  $1F8000    $1CD8BC (and $1E2C5A)       $0D7200-$1CD7FF  ( 985 KB)                         $1CD800-$1CEDFF, $1D0000-$1FB7FF
STE 1.62   4 MB     $400000  $3F8000    $3D89B4                     $0D9200-$1F51FF  (1136 KB) + $1FFE00-$3D87FF (1890 KB)   $1F5200-$1F85FF (13 KB, unidentified, 4 MB only), $3D8800.., $3DB000-$3FB7FF
Mega STE   4 MB     $400000  $3F8000    $3CD8BC                     $0D7200-$1F51FF  (1144 KB) + $1FFE00-$3CD7FF (1846 KB)
```
* **`$100000-$1CD7FF` (2 MB) / `$100000-$1F4FFF` (4 MB) is all zero and is not written by the game, HAGA, TOS or the shipped patches** [obs]: confirmed usable for a loader store, a working copy of the track set and an editor image. `$0D7200..$0FFFFF` is zero too but the road-code cache `$D8000-$E2BFF` (`tb_car`, a `; ram:` area written at run time while driving; zero from `$D9200` on the STE at the standing start, it is not used on the Mega STE) and the 1 MB layout's top (`$E2C50` TOS 2.06 data on a 1 MB machine, `patches/rd_geom.s` note) make it unsafe: use `>= $100000` only.
* **HAGA's top region `$1FB800-$1FFFFF` (2 MB) / `$3FB800-$3FFFFF` (4 MB) is zero and free** [obs] (HAGA itself is `$1F8000-$1FB7FF`): the place where Populous 2 installs its swap-safe part B (HAGA+`$3900-$7000`); the scratch reader ran from there (section 5).
* Payload and road tables as released: `$B2700-$BFFFF` payload (`MSPO` at `$B2700`), `$C0000-$D71FF` `rd_*` tables (`RDG1` at `$C0000`, `SIGOK` `$C0008` = `$FF` at the standing start), `$D8000-$E2BFF` car code cache: untouched by this study.
* At 4 MB the 2 MB boundary is not special: `$1F5200-$1F85FF` (13 KB, non-zero, origin unidentified in the study as well) is the only non-zero island between `$0D9200` and `$3D8800`; keep a working copy below `$1F4FFF` (`$200000-$3D87FF` is free for an editor's undo/extra data at 4 MB only).
* Mega STE vs STE: TOS 2.06 puts its copy 0xB000 lower (`$1CD8BC` vs `$1D89B4`): a 2 MB ceiling of `$1CD000` is correct for both.

## 3. The finish / win rule (question 3)

### 3.1 Static (disasm of the stock race dump, [disasm])
`$7a88-$7b70` is the race loop and it lives INSIDE `jsr $76f4` (called at `$72c4`; `rts` at `$7b70` when `$1024` is negative). `$fa2c` is the end-of-race state machine on `$1024`:
```
fa2c: tst.b $1024 ; beq fadc          ; state 0 = racing
fadc: cmpi.w #$ff,$10ce.w ; bcc rts   ; time bar full = time-out path, no finish
      scan the 32 object slots (lea $2d48 + $38 each) for sprite index $6(a0) == $21 ; its $20(a0) = distance ahead
fb00: cmpi.w #$1f4,d0 ; bgt skip      ; within 500 units:
fb08: $1018 = $10d8 / ($20 - $32) ; $101a = slot ; move.b #1,$1024 ; clr.w $10d2   ; state 1 (time bar stops), the game takes over the car: $10ce8-$10d8c drives it into the object
10cf8: if $20(slot) < $23 : move.b #2,$1024                                  ; reached the object = the line is crossed
fa2c state 2: wait until the closing message is on screen and finished ($11b1 == $ff, $11ab == 0)
      if $10ca > 3 (place) : st $1024 (= $ff) ; else $1024 = 3, bonus count 500/300/100 by place in $11c0, score += ...,  then st $1024
7b6a: tst.b $1024 ; bpl loop ; rts   ; race over
7306: campaign: $102c < 0 / bit 7 = replay flags (time-out); else addq.w #1,$102c ; cmpi.w #$f ; < 15 : next level ($725c) ; = 15 : $75e8 (ending) , $ef46, title $723c
```
Time-out (not a finish): `$11792` adds `$10d2` to the 16.16 time bar `$10ce` every pass; high word >= `$ff` -> `$1226 = 5`, message, then `$1024 = $ff`, `$1027++`; `$1027 < 3`: `$102c |= $80` (replay the same level), else `$102c |= $8000` (game over, title). `$10d2 = ((100 + $102c) * len / 200) + (10 - $edcc[$102c]) * 200` (`$ee64-$ee8e`).

### 3.2 Experiment [obs] (`finish_test.py`, `finish_A.txt`, STE 4 MB patched, restored race snapshot, level 0, joystick up held)
The next object of the stream (`$133a`) was overwritten with level 0's finish type (type word 26, found with `finish_objs.py`), so it spawns within ~100 units; nothing else was touched.
```
[ 7.2s] t1024 0   p5ff8   33  s130c  8   fin_slot (14, 968)     object spawned 968 ahead
[10.1s] t1024 0   p5ff8  298              fin_slot (14, 685)
[12.9s] t1024 1   p5ff8  584   bar10ce 59 fin_slot (14, 398)     <= 500: state 1 (chase); the time bar stops (59 -> 59)
[18.6s] t1024 1   p5ff8  952  s130c 3     fin_slot (14,  77)     the game brakes the car into the object
[21.4s] t1024 2   p5ff8 1013  s130c 0     fin_slot (14,  34)     $20 < $23 -> state 2, car standing at the BAR (snap/finA_02_*.png: "You're too late", place #10)
[24.3s] t1024 2   m11b1 255                                      closing message
[29.9s] t1024 255 l102c 1                                        place 10 > 3 : no bonus, race over, $102c: 0 -> 1 = NEXT LEVEL
```
So: (a) **the finish is the sprite-`$21` object**, nothing else (the world position `$5ff8` was only 1013, the level's `len` is 19,472); (b) object position = `$5ff8` + `$20(slot)` = 1013 + 34 = 1047 = where the stream put it; the chase starts 500 units before the object and the car stops ~34 units before it; (c) **any place completes the level** (place 10 here: the `$10ca > 3` branch skips the bonus only); (d) the `$1024 = 2/3` sequence needs the closing message to run (`$11b1 == $ff`): about 10 s of game time.
The finish object in the stock tracks (`finish_objs.py`, `finish_objs.txt`): every one of the 15 tracks has **exactly one** object whose type has sprite `$21` (the bar), at stream position `pos`; the chase starts at `pos - 500`; `len` is unrelated:
```
lvl  len    finish type  pos    chase start   chase - len        lvl  len    type  pos    chase start  chase - len
  0 19472     26        19958   19458          -14                8 19000   13   18681   18181         -819
  1 19720     51        19961   19461         -259                9 20000   15   19521   19021         -979
  2 19800     83        19991   19491         -309               10 20000   11   19722   19222         -778
  3 19000     26        19199   18699         -301               11 22000    1   20957   20457        -1543
  4 19375     12        19581   19081         -294               12 18500   46   18211   17711         -789
  5 18000     13        17971   17471         -529               13 22000   31   21328   20828        -1172
  6 18626      1        18821   18321         -305               14 23000    4   22117   21617        -1383
  7 20000     30        19526   19026         -974
```
(`len` = word 0 of the minimap block `$57890` = only the time-bar rate (`$ee82`) and the progress/comment code `$fbbc`/`$f2de`.) **Consequences for the editor**: a custom track MUST contain one object of the base level's sprite-`$21` type (the tool finds it: the S5 entry whose sprite word is 33), otherwise the level can only end by time-out; the position of that object is free (the chase starts 500 before it); the time allowed follows the BASE level's `len`, so the editor should warn when `pos - 500` is far from what the player can reach in `((100+lvl)*len/200 + (10-slack)*200)`-time (turbo needed already on level 0: [INFERENCE] arithmetic, not measured).

### 3.3 End of the 15-level campaign [obs] (`finish_B_campaign_end.txt`, same experiment with `$102c` poked to 14)
After the finish `$102c` stays 14 (the `addq` result 15 is only compared: `$731e cmpi.w #$f / bcc $732c`, the value is not stored) and the **ending** runs [obs]: `snap/finB_03_t1024_ff_l000e.png` = the "WELL DONE BOYS!" tavern picture, with the message `$11b1 = 127` text sequence on screen for the rest of the 130 s sample (`$102c` stayed 14). [disasm] `$732c bsr $75e8` (disk-2 check, loads the ending picture at `$8a56`), `jsr $ef46`, `bra $723c` = back to the title (`$724e clr.w $102c` starts a new game); the screens between the picture and the title were not captured [INFERENCE]. For a normal level end (finish A) the game goes to the **spare parts store** (mouse-driven screen with an EXIT button, `snap/hook_race_pos1.png`; `$725c jsr $16718`), then the map screen, then the next race: a campaign adds nothing there. A shorter custom campaign (N < 15) would need the compare `cmpi.w #$f,d0` at `$731e` (4 bytes + the `bcc.b`) redirected; the user decision is "no extra slots", so N = 15.

## 4. The redirect design (question 4)

### 4.1 Sites [disasm] and their bytes in the patched build's RAM [obs]
`check_sites.py` (`sites_check.txt`) on race dumps of STE 4 MB, STE 2 MB, Mega STE 4 MB, Mega STE 2 MB: the original bytes are **identical in the patched build and in the stock race dump**, and **no shipped patch site lies within 0x20 bytes** (the only shipped site near is `rd_init` `$78f6`).
```
site  addr    orig (patched RAM = stock)         len  proposed new bytes                                  purpose
 A    $72c4   4eb9 000076f4  jsr $76f4.l          6   4eb9 <hookA.l>      jsr hookA.l                     wraps the WHOLE race (setup, loop and exit all run inside $76f4; its only caller is $72c4)
 B    $77da   41f9 00058c00 4eb9 0000d6fa         12  4ef9 <hookB.l> 4e71 4e71 4e71   jmp hookB.l          track block fetch (lea $58c00 / jsr $d6fa); hookB ends with jmp $77e6.l
 C    $fda2   41f9 00058c00  lea.l $58c00.l,a0     6   2079 <PTR.l>        movea.l PTR.l,a0              OPTIONAL: stream base pointer, only for blocks > 6144 B (see 4.3)
```
`xref 58c00` finds exactly `$77da` and `$fda2` (study 4). All six stream pointers (`$23c0 $1bb0 $1bb4 $27da $133a $1342`) are `movea.l` / `move.l` (32-bit) in every reader (`xref`: `$ff4a $ff9e $fe7c $feec $fff0 $10048 $e1fe $e22c $e25e`), and the S5 index is `adda.w (type*12)`: a block anywhere in RAM works; the 6144-byte limit is only the `$5a400` load that follows `$58c00`.

### 4.2 `$102c` -> campaign entry and base-level map (proposal)
The campaign has 15 entries `E[0..14]` = `{base level 0..14, block offset, block length, name}`. Hook A (site A) runs around the race:
```
hookA:  tst.b ACT.l ; beq .stk                    ; no campaign loaded: the stock game, bit for bit (jsr $76f4)
        move.w $102c.w,d0 ; andi.w #$f,d0 ; move.w d0,POS.l          ; the campaign POSITION (the campaign loop's own count)
        d1 := E[d0].base ; move.w d1,$102c.w                          ; from here on EVERY per-level table of the game reads the BASE level
.stk:   jsr $76f4.l                               ; race setup + race + exit
        tst.b ACT.l ; beq .x
        d0 := $102c.w & $8080 (flags the race set: $80 time-out replay, $8000 game over) ; or.w POS,d0 ; move.w d0,$102c.w   ; back to position|flags for the campaign loop at $7306
.x:     rts
```
Hook B (site B): `if ACT and E[POS].custom: copy E[POS].block (<= 6144 B) to $58c00 ; clr.b $C0008.l (6.) ; jmp $77e6 else: lea $58c00,a0 ; jsr $d6fa (d1/d2/d3 as the caller set them: the stock load of the BASE level's block) ; jmp $77e6`.
Why swap `$102c` instead of patching tables: the per-level readers are spread over 40 places (4.5); with `$102c = base` inside `$76f4` every one of them sees the base, and only the campaign bookkeeping (`$7306-$7350`, the map screens before `$72c4`, the "LEVEL n" text `$8522`) keeps seeing the position. Proof of the restore in 4.4.

### 4.3 Capacity and the optional site C
Site B copies into `$58c00` (stock capacity 6144 B = L0's block, the largest). The tool builds each block as `S0..S4 (custom) + S5 (the base level's own 12-byte types, verbatim)`, so the S4 type words index the base's types (and their negative sprite indices the base's `$5a400` frames: scenery/objects/colours stay the base's). Stock free room per level is 12..456 B (study 1.3), i.e. a custom track must fit in `6144 - 12*ntypes(base)` for S0..S4: L0 (131 types) leaves 4,572 B (about 417 objects + 106 curve + 315 width/hill pairs, the stock L0), the 30-37-type levels leave 5.7 KB. If an editor needs more, site C + a PTR variable (`$58c00` by default, a big buffer at `>= $100000` for custom entries) removes the cap (32-bit pointers everywhere, see 4.1); not exercised [INFERENCE].

### 4.4 Live proof of A and B [obs] (`hook_test.py`, `trkhook.s`, `hook_test_ste4m.txt`, `hook_test_mste2m.txt`)
Scratch hooks `trkhook.s` (74 + 106 bytes) and a scratch campaign store (15 entries: entry 0 = **base level 3 + the track block of level 5**, entry 1 = **base level 7 with the stock block load**, entries 2..14 = base = position, stock) were loaded through the debugger into a restored standing-start race (STE TOS 1.62 4 MB, and Mega STE TOS 2.06 2 MB), the two sites patched (A `$72c6`: the long `000076f4 -> 00100000`; B `$77da`: `4ef9 00100100 4e71 4e71 4e71`), and the game's own replay path forced (`$102c` bit 7 = restart without title and shop). A breakpoint on `$7306` logs `$102c` and the position variable at every race return. Output = `hook_test_ste4m.txt` (STE 4 MB, final run; earlier runs `_run1/_run2`) and `hook_test_mste2m.txt`:
```
before                          $102c=0000 $57890.len=19472 $58c00=0190000000960002008cfffe (stock L0)  $23c0=00058c14
S1 position 1 (forced $102c=$0081): $102c=0007  $57890.len=20000 (level 7's)  $58c00=0019000000dbfffd00740000 (= level 7's STOCK block head: hook B took the stock path)  $23c0=00058c28
S2 position 0 ($102c=$0083 + POS:=0): $102c=0003  $57890.len=19000 (level 3's)  $58c00=00b4000000280001001effff (= level 5's block head: hook B copied the custom block)
   stream pointers (all inside $58c00..)  STE 4 MB: $1bb0 58dde $1bb4 58e64 $27da 58f02 $133a 591f8 $1342 59a44  (Mega STE 2 MB: 58de6 ...)
S3 normal end ($1024=$ff):           $102c=0001   <- the restore gave position 0, the campaign loop added 1 (without the restore it would read 3 + 1 = 4)
$7306 returns (STE 4 MB): ($102c, POS) = (0080, 0000) after S2's forced exit (flags 0x80 | position 0), (0000, 0000) after S3
Mega STE 2 MB: S1 ok True, S2 ok True, S3 ok True (same values: $102c 7 / 3 / 1, $57890.len 20000 / 19000 / 19000)
```
Screenshots: `snap/hook_S1_pos1_base7_stock.png`, `hook_S2_pos0_base3_block5.png`, `hook_S3_after_race.png` (the shop screen follows a normal race end). `hook_S2_*.png` shows level 3's scenery and colours (desert, sand) around a road with a custom object layout; [INFERENCE] some roadside sprites are "wrong" by construction, because the scratch block is level 5's COMPLETE block (its S5 types index level 5's frames) read against level 3's `$5a400` frames: this is exactly why the tool must append the BASE level's own S5 (4.3). So the swap, the restore, the stock fallback, the custom copy and the `$57890` of the base all work in a live game on both machines; `$102c` is the base for the whole race and the position again for the campaign loop. Not proven here: a full second race of the campaign after the shop (the shop needs mouse clicks), 1 MB (hooks never installed there by design).

### 4.5 Every per-level table or branch keyed by `$102c` (all readers, [disasm] `--xref 102c`) and what it must follow
With the wrapper all of these read the BASE level during the race; the table lists them so the stage-2 gate can check each:
```
reader            keyed by $102c                                                         follows            note
$7720 $27ee[ ]    scenery graphics descriptor -> $1008 (31-35 sectors)                    BASE               art
$777e $291a[ ]    minimap header + nibble path; WORD 0 = race length len (`$57890`)       BASE               len drives time bar rate ($ee82) and progress; minimap not shown in our HUD
$77a2 $28de[ ]    minimap bitmap                                                           BASE               art (unused by the new HUD)
$77c6 $28a2[ ]    TRACK BLOCK descriptor                                                   CAMPAIGN (hook B)  the one table that comes from the campaign file
$77ea $2866[ ]    object frames -> $5a400 (negative sprite indices of S5)                  BASE               the custom S5 must be the base's S5
$7826 $282a[ ]    background / horizon art -> $60800 (d3=$8000)                            BASE               art
$784e cmpi #12/13/14 -> a6 = $116a/$117a/$118a, jsr $166d0 (only levels 12,13,14; every level then runs $18068)   BASE   per-level effect/art loader
$7884 $1362[ ]    colour table (15 x 48 B, copied to $135a)                                BASE               road/grass/edge colours
$7896 $6e26[ ]    word -> $6e5e                                                            BASE
$d7b8 $103a[ ]    per-level 16-byte palette entry ($6e60..) -> $1036                       BASE               sky/scene palette
$dfa8 <5,<10,else tier of 3 car graphics sets ($2156a / $25244 / $28f0c)                    BASE               opponents' cars
$e100 $e14a[ ]    start distance of car slot 4 (5000..17000)                               BASE [INFERENCE]   per-level tuning of an opponent car; may need testing
$ee24 <5,<10,else initial race place $10ca = 6 / 7 / 8                                     BASE               tier = field size
$ee64 $edcc[ ]    time slack word -> $10d2 (time bar rate), and the (100+lvl) factor      BASE               difficulty of the time limit follows the base level
$eef4 $1286[ ]    speech/message stream (distance+$320, sign) -> $12a4                     BASE               talks along the base's road (distances fit the base's `len`)
$fb50 ==4,==9,<14 closing-message choice ($6527 / $64b1 / $64f2 / $6568)                  BASE
$10b32 <5 ... tiers   minimap-position constants ($10ae2..$10b0a)                           BASE               minimap only
$11a60 <5,<10 AI tier (3/4/5)                                                              BASE               opponent behaviour
$11b64 lvl>>2 + $11 -> $24(a0)                                                              BASE
$11f90 $11fae[ ]  byte table when $1028 is set (race loading)                               BASE
$168b0 <=1        tutorial-style init $17112 on levels 0,1                                  BASE [INFERENCE]   keeps the first two base levels' special case
$8522 (and $7280-$72b4 tier -> $1029)  "LEVEL n" text, world index of the map screens       POSITION           runs outside $76f4: automatically the position
```

### 4.6 What does NOT need the base: nothing in the track block depends on `$102c`; `rd_init`/`rd_geom`/`rd_draw` tables depend on `$1316` and the colour table copy `$135a` only (study 4, `integration.md`): base-keyed, so a swapped track needs no road re-init beyond what the setup sequence already runs.

## 5. The campaign-disk read path (question 5)

### 5.1 The model: Populous 2 / Hunter in this repo
* `games/done/populous-2/patches/pop2_save.s` (713 lines): part A (game context) checks HAGA by signature (`+$17be`, `+$1166`, `+$1372`, machine type 4 refused), installs part B (position independent, `$700` B template) into HAGA's own top region `HAGA+$3900`, then calls it; part B runs `Fopen/Fseek/Fread/Fclose` (and `Fcreate/Fwrite/Fclose + Dfree` for saves) INSIDE HAGA's TOS window: `+$17be` (MFP enables off), `+$1166` (fade + swap TOS's low RAM in), private stacks and `usp`, GEMDOS through `trap #1`, `+$1372` (swap out), MFP restore from `HAGA+$33c4`, IKBD ACIA drain and the game's parser reset; critical-error vector `$404` replaced by a stub that returns the error. It also has a floppy mode (drive A/B: forget the BIOS cache buffers of drives 0/1 before every call, because TOS's media-change detection does not run while the game owns the interrupts).
* Hunter (`games/done/hunter/patches/sav_sync.s`, `work/notes/save.md`) uses PP's own `D15R` loader and only adds the durability `Dfree` after a write. Neither is needed for READING; stage 2 is read-only.
* Moonshine differences (all handled in the scratch reader): HAGA base is at `$2dc` (not `$328`), the IKBD parser state is `$6102 $6103 $610e` (handler `$cfb4`: pending-joystick flags and the mouse packet counter; not Pop2's `$2022`), HAGA's current directory is `FILES\` (RUNME's `Dsetpath`), HAGA+`$83` is 2 on the STE and 3 on the Mega STE.

### 5.2 Prototype (scratch only): `trkread.s` (756 B), `callstub.s`, `call_trk.py`
`trk_read(a0 = path, a1 = destination, d1 = max bytes) -> d0 = 0 / GEMDOS error / $cd too long / $dd short, d1 = bytes`; part A installs part B into HAGA+`$3900` on first use. Driven from Hatari with the debugger: at the next execution of the game's flip routine `$d1ca` a breakpoint script loads the blob, the stub and the parameters, sets `PC` to the stub (`r pc=$100400`), the stub saves all registers, calls, stores the result and jumps back to `$d1ca`; `e VBL` is printed at the start and at the stub's `done`. The call is made in the RUNNING race (supervisor, `SR = $2304` at entry in every run), standing and driving (joystick up held).
```
test (snapshot, machine)                       file                          result   bytes    cost        race afterwards                                   log
STE 1.62 4 MB, standing                        FILES\MSTRACKS.TRK (host dir)  d0=0     122892   37 VBL      $100e advancing, picture intact (after_call.png)  call_ste4m_hd.txt
Mega STE 2.06 2 MB, driving                    FILES\MSTRACKS.TRK            d0=0     122892   33 VBL      $5ff8 1788 -> 2208, $130c 10, $6105=1 kept        call_mste2m_hd_driving.txt
STE 4 MB, standing, floppy in A (hatari-option --disk-a)  A:\MSTRACKS.TRK      d0=0     122892   799 VBL     race runs, screenshot clean                       call_ste4m_floppy.txt
STE 4 MB, driving                              A:\MSTRACKS.TRK               d0=0     122892   803 VBL     $5ff8 1788 -> 2208 $130c 10                       call_ste4m_floppy_driving.txt
Mega STE 2.06 2 MB, driving                    A:\MSTRACKS.TRK               d0=0     122892   950 VBL     $5ff8 1758 -> 2178                                call_mste2m_floppy_driving.txt
Mega STE 2.06 4 MB, driving, TWO calls in a row A:\MSTRACKS.TRK              d0=0 x2  122892   948 / 876   $5ff8 2676 -> 3015                                call_mste4m_floppy_2calls.txt
STE 4 MB, driving, floppy A, wrong name        A:\NOSUCH.TRK                 d0=-33   0        102 VBL     $5ff8 1478 -> 1898, $6105=1                       call_ste4m_floppy_noname.txt
STE 4 MB, standing, NO disk in A               A:\MSTRACKS.TRK               d0=-33   0        835 VBL (16.7 s)  race runs                                 call_ste4m_nofloppy.txt
STE 4 MB, driving, HD file missing             NOSUCH.TRK                    d0=-33   0         31 VBL     race runs                                         call_ste4m_hd_missing.txt
```
In every success case `snap/dest.bin` (read back with `savebin` from the destination `$120000`) is **byte-identical** to the file (`crc 0xdb1845da`, `data compare ... True`); the IKBD parser state after the call is idle (`$6102 $6103 $610e = 0`); `$6105` keeps the held joystick bit (no event was lost in these runs); the race loop keeps counting (`$100e`), the road is drawn, the speed variable is unchanged (`$130c 10`). The test file is `work/trackloader/disk/MSTRACKS.TRK` (the 15 stock blocks in 8 KB slots) and `disk/campaign.st` (720 KB FAT12 image, `mk_testdisk.py`).
**Cost model**: floppy about 154 bytes per VBL (7.7 KB/s emulated); the HD read is dominated by the two 64 KB low-RAM swaps and the 8 KB copy loop (about 0.6-0.7 s, independent of size up to 120 KB). A realistic campaign file (15 blocks of 4-6 KB, about 70 KB) therefore takes about 9 s from a floppy, 0.7 s from the HD. A blind attempt with no disk in A costs 16.7 s (TOS's retries): **never probe the floppy automatically**.
Not tested: keys/joystick events that arrive DURING the window (they are lost: MFP enables are off, the ACIA is drained afterwards; a joystick release during the call would leave `$6105` stale until the next event), real hardware (HDDRIVER/ACSI swaps a larger low range, `$8..$1B6C8`; HAGA's own routines do it), a disk change between two calls (the BCB-forget loop is in the code and the two-call run read the same disk twice; a real swap was not exercised), TT/Falcon (type 4 is refused in the blob; the TT needs the PMMU alias care of Pop2's blob).

### 5.3 Floppy build (`work/notes/floppy.md`)
There is **no HAGA and no TOS** in the floppy build [floppy.md sections 2, 7]: the game boots from disk A's boot sector and runs its own FDC driver (`$cac0`, sole entry `$d6fa`: raw sectors, linear sector number `< $320` = drive A side 0, device word bit 2 = side 1, 10 sectors per track, no TOS `Floprd`, bounded waits, two-drive aware) and asks for disk 2 itself (`$76f4`: `jsr $d788` = boot-sector check on the disk in drive A, "Insert Disk 2 and press a key", loop; `$75e8` does the same for the ending). A campaign disk there is read with THAT driver (`jsr $d6fa` into a buffer at `>= $100000`), not GEMDOS: a different, smaller code path (about 300 B [INFERENCE: estimate]: read the boot sector/BPB, scan the root directory for `MSTRACKS.TRK`, take the first cluster and read the file's sectors, either following the FAT12 chain or assuming the contiguous file the PC tool writes, one `$d6fa` call per run), a disk-ID/prompt flow like the game's own, and a campaign disk in the game's own 10-sector geometry: `mformat -t 80 -h 2 -s 10` makes a valid 819,200-byte FAT12 image that holds the same `MSTRACKS.TRK` [obs: `mformat`/`mcopy`/`mdir` accept it (`minfo`: 10 sectors per track, 2 heads, 80 cylinders, media `f0`); that the 720 KB 9-sector `campaign.st` of the HD tests would not match the game's 10-sector driver is an INFERENCE]. A trigger is needed while disk 1 is in the drive; whether disk 1 is still needed after the title is [INFERENCE] (the game asks for it again only through `$d778`, a path no caller was found for in the dump, floppy.md section 7), and the game asks for disk 2 itself at the first race, so a campaign disk read before that costs no extra swap if the user puts disk 2 back in. Feasible at >= 2 MB (`$100000+` is free there as well: no HAGA, no TOS copy), **not prototyped and not proven**. Recommendation: **campaigns HD-only for v1.1**; the floppy build later as its own stage with the same file format on an 800 KB FAT12 disk.

## 6. `rd_geom` standing-reuse invalidation (question 6)
[disasm `patches/rd_geom.s`, obs `snap/megaste_4096.bin`] When `$130c == 0` and `SIGOK ($C0008) != 0`, `rd_geom` compares 33 words (`sigtab`: `$1308 $130a $130c $1316 $1318 $13ae $1bba $1bb8 $23c6 $102c $13a2-$13ac $23bc $23be $27c8 $1bb0 $1bb2 $1bb4 $1bb6 $23c0 $23c2 $27da $27dc $27ca-$27d4`) with the saved copy `SIGBUF ($C0340)` and, if equal, copies the saved output (`SAVE $C0400`: `$4724-$4f77`, `$23c4`, `$131c`, `$1320`) back instead of recomputing. [obs] at the standing start of the Mega STE 4 MB race: `SIGOK = $FF`, live key words == `SIGBUF` (33/33 equal), `$102c` in the key = 0, stream pointers `$1bb0 = 5:8db2, $1bb4 = 5:8e3c, $23c0 = 5:8c14, $27da = 5:8ec6` (`$58c00`-relative).
* **The key contains `$102c` and the six stream pointers**, so a different base level, or a different block whose stream lengths differ, mismatches by itself. The hazard is a block that has the same base AND identical stream pointers but different VALUES (an in-place edit of the working copy while standing, or two campaign entries of the same base with equal stream byte lengths): then the standing frame of the old track would be copied back.
* **Cheapest invalidation: `clr.b $C0008.l`** (6 bytes `4239 000c 0008`), executed once per race setup in hook B (done in `trkhook.s` for custom entries) and by the editor after any ring/stream write while standing. `SIGOK` is the first byte of the tool-checked `; ram: $C0000-$CAFFF` area, set again by `rd_geom` at its next `.cap` (`st SIGOK` at `rd_geom.s` line 279); nothing else holds a copy.
* [INFERENCE] a moving frame (`$130c > 0`) also changes the key words (positions), so the reuse cannot survive one real pass; the invalidation matters only for standing frames, i.e. the start grid and the editor's preview.

## 7. Recommended stage-2 design

### 7.1 Scope (user decisions 2026-11-20)
Tracks from a FILE at >= 2 MB on STE / Mega STE (HAGA type 2 or 3); a campaign file = 15 entries (base level + track block + name), replacing the stock tracks in order; 1 MB and every other machine run the stock game unchanged; no minimap work, no race-length edit; the campaign file is also what is shipped on a campaign disk.

### 7.2 Sites and code (payload, all `min-RAM 2 MB`)
1. **Gate (trampoline)**: `core.s` gets a second site table `TABLE2` whose sites are verified and applied only if `cmpi.l #$200000,$42e.w / bcs` (phystop >= 2 MB) **and** `HAGA+$83 in {2,3}` (`movea.l $2dc.w,a0 / move.b $83(a0),d0`). [obs] `gate_probe.py` (breakpoint on the trampoline entry `$b2708` of the cold-booted shipped build, `gate_probe_ste2m.txt`, `gate_probe_mste2m.txt`): at that instant `$2dc = $1F8000`, `$42e = $200000`, `$436 = $1F8000`, `HAGA+$83 = 2` (STE) / `3` (Mega STE), `HAGA+$af = 0`, the three signatures `4dfa1c04 / 45fa0e1e / 123aed0f` present, `HAGA+$3228 = 602a`, SR `$2304` (supervisor, IPL 3), `$b2700` still zero (the marker is written by the trampoline). 4 MB: `$2dc = $3F8000` in the race dumps; the hook instant was probed at 2 MB only. Tool change points: `tools/msrpatch.py` header parsing next to `requires`/`conflicts` (line ~262: a `; min-ram: 2048` key), `site_list()`/`build_image()` (line ~457: emit the sites of min-ram patches as a second table after the first, same pool), `core_segment()`/`patches/core.s` (a second verify/apply loop behind the gate). At 1 MB TABLE2 is skipped: **no site is patched**. (`patches/` and `tools/` are frozen for this study; this is the lead's v1.1 work.)
2. **`ed_wrap` (site A `$72c4`)** and **`ed_fetch` (site B `$77da`)**: hookA/hookB of 4.2 (about 180 B, `trkhook.s` is the working prototype). Variables `ACT.b`, `POS.w`, `TRIED.b` and the pointer to the campaign store live in the payload's data area (or a `; ram:` line).
3. **`ed_load` = the HAGA-window reader** (`trkread.s`, 756 B: part A + part B template; port of Pop2 part A/B, read-only): `ed_load(path, dest, max)`. Part B is copied to `HAGA+$3900` on first use, the data/stacks/bounce buffer sit above it (`HAGA+$3900-$7000`, free in both HAGA sizes [obs 2]).
4. **Validation** (in the loader, before `ACT` is set): magic, version, 15 entries, `base < 15`, `offset+len <= filesize`, `len <= 6144` and even, a header sum/CRC; per block a cheap structural walk (five streams end with a zero count inside `len`, S5 entries start with `$ff00`); anything wrong rejects the whole file (stock game, nothing half-applied). The PC tool does the full validation (decode the six streams, check the four ring sums >= `len + 1024`, one finish object of the base's `$21` type, object slots).
5. **Load moments**: (a) HD: `FILES\MSTRACKS.TRK` at the first `hookA` of a boot (`TRIED`), 0.6 s miss / 0.7 s hit [obs 5.2]: zero UI; (b) campaign disk in drive A: only on an explicit key at the title (candidate: F10 = scancode `$44` in `$60ff`, polled in the title loop `$7242`/`$73e6`; the F-key flow `$7988` already reads `$60ff`; **not tested** [INFERENCE]) with an on-screen "INSERT CAMPAIGN DISK / LOADING" text from the game's own message routine and never an automatic probe (16.7 s with an empty drive).
6. Campaign file `MSTRACKS.TRK` (proposal): header `'MSTK'`, version.w, count.w (= 15), sum/CRC.l, name[24]; 15 entries `{base.b, flags.b, offset.l, len.w, name[12]}`; the blocks back to back, each complete (`S0..S4` + the base's S5), <= 6144 B. About 68 KB if every track were as large as the stock ones (the 15 stock blocks are 3584-6144 B including sector padding = 67,584 B), at most 15 x 6144 = 92 KB.

### 7.3 RAM map (>= 2 MB, measured in section 2)
```
$0B2700-$0BFFFF   payload as released (+ the ~1 KB of hooks and reader; headroom is 14 KB)        $0C0000-$0E2BFF  rd_* tables and car cache as released
$100000-$10FFFF   scratch for the loader / stage-3 editor code image                                [free, zero, all four machines]
$110000-$12FFFF   campaign store (file as read: <= 128 KB; <= 94 KB used)
$130000-$1CCFFF   working copy / editor data / undo (2 MB ceiling $1CD000; 4 MB ceiling $1F4FFF; extra $200000-$3CD000 at 4 MB only)
HAGA top region (HAGA+$3900-$7000 = $1FB900-$1FF000 at 2 MB, $3FB900-$3FF000 at 4 MB): reader part B (installed on first use)
never: $1CD800-$1FB7FF (2 MB) / $3CD800-$3FB7FF (4 MB) = TOS copy + HAGA; $1F5200-$1F85FF at 4 MB (unidentified)
```
The read destination may be anywhere (the reader copies from its bounce buffer after the swap-out), so the store may even be read directly into its final place.

### 7.4 1 MB inertness argument and how to gate it
* The three RAM sites (A, B, optional C) are in TABLE2 and are applied only when phystop >= 2 MB and HAGA type is 2/3. At 1 MB no byte of the game code changes: every executed instruction is the release's (strongest form; the unreferenced hook bytes in the payload area are never entered). The existing A/B gates (`msrabtest.py` STATE gate over `$1000-$13ff,$29c8-$34ff,$4500-$4fff,$dae6`, pixel gates) then repeat trivially at 1 MB, and the release md5 of `RUNME.TOS`/`HAGA` changes only by the added TABLE2/hook bytes in the payload image (the tool must still refuse a HD build without `pp_bigram_cache`: already so).
* At >= 2 MB without a campaign (`ACT = 0`): hook A is `tst.b ACT / beq / jsr $76f4 / tst.b / beq / rts` (about 40 cycles per race), hook B is the stock `lea / jsr` replayed: behaviour identical to the release except for those instructions. [INFERENCE: A/B state gates on 2 MB not run.]
* The reader refuses to run (`d0 = -1`, no side effect) when HAGA's signatures or machine type do not match; a Falcon (type 4) or a TT (5) never gets the sites (gate in TABLE2), and a missing/invalid file leaves `ACT = 0`.

### 7.5 PC-side work that belongs to stage 2
`tools/msrtrack.py` (build from JSON/decoder tables, validate, make the base-matched block with S5 copied from the base level, write `MSTRACKS.TRK`, make an 800 KB or 720 KB FAT12 campaign disk with mtools-equivalent pure Python as `nebcampaign.py` does) and a validator mirroring the in-game checks (as `work/editor/ovl.py` does for Nebulus).

## 8. Costs and risks
Costs (agent-hours, estimate; the study's 14 h for stage 2 grows because the campaign disk and the base-level map were added): TABLE2 + `; min-ram` in `msrpatch.py`/`core.s` 3 h; hooks A/B (+ C optional) from the prototype 2 h; reader port (prototype exists) 2 h; load triggers + messages + F-key 3 h; file format + PC tool + validator + disk images 7 h; gates (1 MB byte-identical A/B, STE/Mega STE 2 MB and 4 MB cold boots into a campaign race, restart/time-out/finish/ending with a custom campaign, floppy-image read at 2/4 MB) 5 h; docs 2 h = about 24 h. Floppy build: +8-10 h [INFERENCE].
Risks: (1) blocking window: 0.7 s (HD) / ~9-16 s (floppy) with the screen faded and IRQs off; keys pressed during it are lost [obs not run]; (2) real hardware untested everywhere (HDDRIVER/ACSI bigger swap, real FDC timing, media change handling: the BCB-forget is a Pop2 mechanism proven there on Hatari); (3) TT/Falcon excluded by the gate; (4) the trigger key and its screen are untested; (5) the 6144-byte block cap (4,572 B of S0..S4 on a 131-type base): site C removes it, untested; (6) `e14a`/`$168b0` base-vs-position semantics not proven (4.5); (7) a custom track without the base's `$21` object can never be won (tool must refuse); (8) `build/hd` is stale: stage-2 gates must run on a freshly built folder (a `--out /tmp/...` build), never on `build/hd`.

## 9. Files (for the lead to commit): notes + scratch only
New: `work/notes/trackloader.md` (this file). New under `work/trackloader/`:
* scripts: `run_hatari_env.sh` (private HOME + local Hatari), `boot_snap.py` (cold boot to a REAL race + RAM dump + memstate; the memstate shortcut writes `$HOME/.config/hatari/hatari.sav`, deleted first because Hatari blocks on an overwrite dialog), `boot_matrix.sh` (the four cold boots), `boot_stale.py` (the stale `build/hd` 4 MB boot), `gate_probe.py` (values at the trampoline entry), `zeromap.py`, `check_sites.py`, `finish_objs.py`, `finish_test.py`, `call_trk.py`, `call_matrix.sh`, `hook_test.py`, `mk_testdisk.py`, and the exact queues that produced the logs: `phase4.sh` (finish A/B, first hook run, stale boot, STE 2 MB boot) `phase5.sh` `phase6.sh` `phase7.sh` `phase8.sh` `phase9.sh` (hook runs `_run1/_run2` = earlier versions of the output, HD file call log, gate probes);
* sources: `trkread.s` (HAGA-window reader prototype, 756 B), `callstub.s` (debugger-driven call), `trkhook.s` (hook A/B prototype); assembled `*.bin`, `*.lst`, `param.bin`, `store.bin`, `apply*.txt`, `at7306.txt`, `end.txt`, `gp.txt` are regenerable;
* logs: `boot_*.txt`, `call_*.txt`, `finish_*.txt`, `hook_test_*.txt`, `gate_probe_*.txt`, `sites_check.txt`, `finish_objs.txt`, `snap/*.zeromap.txt`, `snap/*.png` (screenshots; `snap/ste2m_hd.png` = the title screen that `boot_to_race()` reports as "in race");
* large and regenerable, **do not commit**: `snap/*.bin` (RAM dumps of the four race standing starts, 2-4 MB each), `snap/*.sav` (memstates, 0.6-0.7 MB each, restorable with `Moonshine(snapshot=...)`; useful for stage-2 gates), `snap/dest.bin`, `disk/MSTRACKS.TRK`, `disk/campaign.st` (both regenerated by `mk_testdisk.py`).

## 10. Reproduce
```
cd games/in_progress/moonshine-racers
mkdir -p /tmp/msrl_dist && (cd /tmp/msrl_dist && unzip -o -q $OLDPWD/dist/MoonshineRacers_hd_v1.0.zip)        # the shipped build
work/trackloader/run_hatari_env.sh python3 work/trackloader/boot_snap.py --game /tmp/msrl_dist/MOONSHR --machine ste --mem 4096 --out work/trackloader/snap/ste_4096 --dump
python3 work/trackloader/zeromap.py work/trackloader/snap/ste_4096.bin 4
python3 work/trackloader/mk_testdisk.py ; vasmm68k_mot -Fbin -m68000 -nosym -o work/trackloader/trkread.bin work/trackloader/trkread.s   # (callstub.s, trkhook.s likewise)
work/trackloader/run_hatari_env.sh python3 work/trackloader/call_trk.py --snap work/trackloader/snap/ste_4096.sav --machine ste --mem 4096 --path 'A:\MSTRACKS.TRK' --floppy work/trackloader/disk/campaign.st --drive
work/trackloader/run_hatari_env.sh python3 work/trackloader/finish_test.py --snap work/trackloader/snap/ste_4096.sav --machine ste --mem 4096 --secs 90
work/trackloader/run_hatari_env.sh python3 work/trackloader/hook_test.py --snap work/trackloader/snap/ste_4096.sav --machine ste --mem 4096
```
(Hatari writes the memstate with `hatari-shortcut savemem` to `$HOME/.config/hatari/hatari.sav` and blocks on an overwrite dialog if it exists: `boot_snap.py` deletes it first.)

## 11. Addendum (late runs and alignment with stage 1)
### 11.1 Site C (pointer variant, no copy, no 6144-byte cap) is proven live [obs] (`trkhook2.s`, `hook_test.py --variant ptr`, `hook_test_ste4m_ptr.txt`)
Hook B sets a long `PTR` (the block's address INSIDE the store at `$110000+`, or `$58c00` after the stock load) and site C `$fda2` becomes `movea.l PTR.l,a0` (`2079 00100f10`). STE 4 MB, position 0 = base 3 + level 5's block: `$102c = 3`, `$57890.len = 19000`, `$58c00` untouched (still level 7's stock block from the previous race), stream pointers `$23c0 = $111020`, `$1bb0 = $1111e6`, `$1bb4 = $111264`, `$27da = $111302`, `$133a = $1115f8`, `$1342 = $111e44` (all above 1 MB), the race ran (`$100e` 870 -> 889, no crash), the restore gave `$102c = 1` and the `$7306` log shows `(0080, 0000)` then `(0000, 0000)`. So all six stream pointers are 32-bit clean for a block anywhere in RAM. Weakness: the curve ring `$1bbc` is all zero for the first 1024 units of level 5, so the script's `equal ... True` is weak evidence (pointers + surviving race are the evidence). The script's "S2 ok: False" line is only its `$58c00` wait condition, which cannot hold in this variant. **NOT run (stopped at the request budget)**: the ptr variant on Mega STE; site D (`--count`, `trkhook2.s hookD`); the stage-1 artifacts (`tools/msrtrack.py campaign new --stock` 64,676 B file and `disk` image) through the HAGA reader (`call_trk.py --ref` exists for it). Treat those as NOT proven; the bytes of site D are only checked against RAM.
### 11.2 Alignment with `work/notes/trackformat.md` / `tools/msrtrack.py` (stage 1, written in parallel; it supersedes my 7.2.6 file proposal)
* Use ITS campaign file (header 16 B, 40 B entries, canonical blocks incl. end word, S5 = the base's table, block <= 8192 B, count 1..15, CRC-32s; the stock 15-track file is 64,676 B, so a floppy read is about 8.4 s at the measured 7.7 KB/s and the HD read 0.7 s).
* Block <= 8192 B is larger than the 6144-byte stock buffer: **site C (11.1) is therefore mandatory, not optional**, and hook B needs no copy (it just computes `PTR = store + entry.offset`).
* count < 15 is allowed by that format: the end-of-campaign test must follow it: **site D `$731e`** (`0c40000f 6408` -> `4ef9 <hookD>`, hookD = `cmp.w COUNT.l,d0 / bcc.s end / jmp $7324.l / end: jmp $732c.l`; bytes verified in the patched RAM of all four machines by `check_sites.py`, `sites_check.txt`; not run live).
* Add to its validator: **E-FINISH** (a block must contain at least one object whose type, in the base's S5, has sprite `$21`: otherwise the level can only end by time-out, section 3), W-FINISH (chase start `pos - 500` vs the time the base's `len` allows). Its "Not checked: the exact win/finish rule" is answered by section 3.
* In-game validation: magic, version, count, file length, table CRC (616 B at 15 entries, cheap), per-entry flags/base/offset/len, structural walk of each block; the per-block CRC-32 is for the PC tool (a table-driven CRC over 65 KB costs about 0.5 s at 8 MHz [INFERENCE: arithmetic]).
* Its campaign disk is 720 KB / 9 sectors (TOS reads it; the HD path is what was tested, with an mtools image of the same geometry). The floppy BUILD's own driver is 10-sector (5.3): an 800 KB variant (`mformat -t 80 -h 2 -s 10`) would be needed there.
### 11.3 Final recommended site list for the lead
A `$72c4` (wrap, base/position swap) · B `$77da` (block fetch: sets PTR, stock fallback) · C `$fda2` (`movea.l PTR`) · D `$731e` (campaign count), all in TABLE2 (>= 2 MB and HAGA type 2/3), plus the reader of 5.2. `rd_geom` invalidation `clr.b $C0008.l` in hook B.
