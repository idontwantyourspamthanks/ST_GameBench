# Hunter hot paths (HunterBench; 8 MHz STE, TOS 1.62, 1 MB, snapshots in work/snapshots)

Raw data: `work/prof/<snapshot>.txt` (`addr cycles count`, hex addr; Hatari `profile cycles`+`profile counts` over ~250 VBL),
dump `work/dumps/ram_foot_stand.bin` (code is identical in all snapshots). Tools: `tools/hprof.py` (function buckets =
jsr/bsr/jmp targets; exclusive cycles), `Hunter.profile_cc`, `Hunter.site_trace`. Frames = executions of the flip instruction $5fee.
Walk/drive scenarios held the cursor key (`hold('Up')`, `Up+Left`) while profiling, because a restored snapshot has the stick released.

## 1. Frame-time split (cycles between `$253e` loop-top hits, `e CycleCounter`; call sites listed in frameloop.md)
| stage | foot_stand | foot_walk | car_stand | car_drive | car_turn |
|---|---:|---:|---:|---:|---:|
| $5f6a frame-pace wait + flip (+VBL spin) | 43,882 (2.5%) | 96,438 (9.5%) | 72,786 (5.0%) | 71,833 (6.4%) | 88,121 (7.4%) |
| $6000 | 276 (0.0%) | 276 (0.0%) | 276 (0.0%) | 276 (0.0%) | 275 (0.0%) |
| $7db0 | 2,592 (0.1%) | 2,592 (0.3%) | 2,592 (0.2%) | 2,592 (0.2%) | 2,592 (0.2%) |
| $269c | 19,156 (1.1%) | 18,563 (1.8%) | 16,500 (1.1%) | 20,054 (1.8%) | 19,568 (1.6%) |
| $372c | 2,027 (0.1%) | 2,021 (0.2%) | 1,844 (0.1%) | 2,278 (0.2%) | 2,141 (0.2%) |
| $c84a dither/ground fill | 60,324 (3.4%) | 60,383 (5.9%) | 60,483 (4.2%) | 59,799 (5.3%) | 59,828 (5.0%) |
| $41d8 | 25,769 (1.5%) | 24,365 (2.4%) | 22,923 (1.6%) | 22,670 (2.0%) | 22,731 (1.9%) |
| $3990 3D RENDER | 1,556,050 (88.3%) | 753,816 (74.2%) | 1,211,539 (84.0%) | 888,680 (79.2%) | 936,854 (78.7%) |
| $406a (cond.) | 28 (0.0%) | 28 (0.0%) | 28 (0.0%) | 28 (0.0%) | 28 (0.0%) |
| $96f6 | 52,595 (3.0%) | 57,054 (5.6%) | 53,609 (3.7%) | 53,520 (4.8%) | 58,471 (4.9%) |
| **frame total (cycles)** | 1,762,721 (21 frames) | 1,015,560 (34 frames) | 1,442,603 (24 frames) | 1,121,753 (35 frames) | 1,190,632 (30 frames) |

Reading: logic (everything except $3990) is 12-26 % of the frame; the 3D render `$3990` is 74-88 %. The `$5f6a` bucket contains
the flip (`$5fd2`) and the VBL spin (`$aaa2/$aab4`, idle). Walking/driving are cheaper than standing at the HQ only because the
view contains less geometry; **per-VBL quantisation matters**: a frame takes a whole number of VBLs (stand: 1.763 M cycles = 11.0 VBL
= 4.5 fps; a 1 % saving would cross to 10 VBL = +10 % fps).

Render stages, from exclusive-cycle shares of the walking profile (functions below; stages are my grouping, [INFERENCE] for names not in the code):
scan conversion+edge walk 38.6 % ($7518) + edge slopes 10.3 % ($7450) + span fills ~12.5 % ($7af0, $7a24, $7952) = ~61 %;
vertex transform 3.3 % ($5452,$54f4); projection 3.2 % ($5268); scene/cell loop 2.4 % ($3ada); template copy 3.5 % ($c91a);
dither fill 2.9 % ($c84a); idle spin 6.4 % ($aab4); IKBD poll delays 2.4 % ($afc4).

## 2. Top-15 functions, exclusive cycles (calls/frame = executions of the function's first instruction)
### foot_stand (standing at the HQ; 1.77 M cycles/frame)
```
frames=20 total_cycles=35337084 (221 VBL)  cycles/frame=1766854
func     excl_cyc   share  calls/frame  cyc/call
$07518   13440028  38.03%     115.00       5843
$07450    3984364  11.28%      46.05       4326
$07af0    3251612   9.20%      11.00      14780
$05452    2221128   6.29%     131.00        848
$05268    1675160   4.74%       7.00      11965
$0c91a     950960   2.69%       1.00      47548
$0afc4     847996   2.40%      11.00       3855
$0c84a     798256   2.26%       1.00      39913
$07a24     690780   1.95%     153.05        226
$0aab4     686424   1.94%    1070.35         32
$03ada     683088   1.93%       1.05      32528
$10f52     625812   1.77%       0.00          0
$054f4     585672   1.66%      56.00        523
$0a648     565840   1.60%       0.00          0
$07952     509904   1.44%      12.00       2125
```
### foot_walk (Up held)
```
frames=26 total_cycles=35307904 (220 VBL)  cycles/frame=1357996
func     excl_cyc   share  calls/frame  cyc/call
$07518   13622688  38.58%      69.62       7526
$07af0    3719672  10.53%       0.00          0
$07450    3625480  10.27%      36.62       3808
$0aab4    2240836   6.35%    2689.62         32
$0c91a    1238920   3.51%       1.00      47651
$05268    1125372   3.19%       3.65      11846
$0c84a    1026512   2.91%       1.00      39481
$03ada     858236   2.43%       1.00      33009
$0afc4     848908   2.40%       8.46       3859
$054f4     600588   1.70%      26.46        873
$05452     575524   1.63%      74.08        299
$0a648     565840   1.60%       0.00          0
$10f52     553828   1.57%       0.00          0
$0c8c0     496136   1.41%       0.00          0
$03990     394868   1.12%       1.00      15187
```
### car_drive (Up held, car blocked/slow at the shore)
```
frames=31 total_cycles=35333108 (220 VBL)  cycles/frame=1139777
func     excl_cyc   share  calls/frame  cyc/call
$07518   11802432  33.40%      39.23       9706
$07450    3464668   9.81%      34.45       3244
$07af0    3033192   8.58%       1.03      94787
$05452    2388056   6.76%      76.39       1008
$0aab4    1751264   4.96%    1763.16         32
$0c91a    1475332   4.18%       1.00      47591
$0c84a    1195604   3.38%       1.00      38568
$05268    1057736   2.99%       4.13       8264
$03ada    1050832   2.97%       1.00      33898
$054f4    1028668   2.91%      45.42        731
$0afc4     847020   2.40%       7.10       3850
$10f52     727836   2.06%       0.00          0
$0c8c0     614544   1.74%       0.00          0
$0a648     565840   1.60%       0.00          0
$03990     433144   1.23%       1.00      13972
```
### hills_stand (hilly terrain at X151 Y50)
```
frames=32 total_cycles=35285830 (220 VBL)  cycles/frame=1102682
func     excl_cyc   share  calls/frame  cyc/call
$07518   11723054  33.22%      58.34       6279
$07af0    3653884  10.36%      10.72      10653
$07450    3346656   9.48%      25.16       4157
$05452    1572608   4.46%      67.91        724
$0c91a    1522040   4.31%       1.00      47564
$044a8    1234876   3.50%     263.66        146
$0c84a    1175012   3.33%       1.00      36719
$03ada    1036696   2.94%       0.97      33442
$05268     974796   2.76%       1.88      16247
$0aab4     960156   2.72%     935.41         32
$0afc4     847872   2.40%       6.88       3854
$0c8c0     681984   1.93%       0.00          0
$10f52     597940   1.69%       0.00          0
$0a648     565840   1.60%       0.00          0
$041d8     523432   1.48%       1.00      16357
```

### The five most expensive functions (foot_walk profile; the same five lead in every scenario)
| # | function | share | calls/frame | cycles/call | role |
|---|---|---:|---:|---:|---|
| 1 | `$7518` | 38.6 % | 69.6 | 7,526 | polygon scan conversion / edge walk |
| 2 | `$7af0` | 10.5 % | (entered by computed jumps; ~0 counted entries) | | span fill handlers |
| 3 | `$7450` | 10.3 % | 36.6 | 3,808 | edge slope setup (`divs`) |
| 4 | `$aab4` | 6.4 % | 2,690 | 32 | idle: VBL / min-frame-time spin |
| 5 | `$c91a` | 3.5 % | 1.0 | 47,651 | background template copy |
(stand: `$7518` 38.0 %, `$7450` 11.3 %, `$7af0` 9.2 %, `$5452` 6.3 % = vertex transform, `$5268` 4.7 % = projection.)

## 3. Top 8: disassembly excerpts and role
### `$7518` - polygon scan converter: bounding box, edge-table build, per-scanline edge interpolation; dispatches span fills
```
sub_007518:
007518:  1018                 move.b   (a0)+, d0
00751a:  61000508             bsr.w    $7a24  ; sub_007a24
00751e:  49faf5d0             lea.l    $6af0(pc), a4
007522:  4240                 clr.w    d0
007524:  1018                 move.b   (a0)+, d0
007526:  08800007             bclr.b   #$7, d0
00752a:  6712                 beq.b    $753e
00752c:  4a2d1618             tst.b    $1618(a5)
007530:  670c                 beq.b    $753e
007532:  0240000f             andi.w   #$f, d0
007536:  d0c0                 adda.w   d0, a0
007538:  2b481600             move.l   a0, $1600(a5)
00753c:  4e75                 rts      
00753e:  7270                 moveq    #$70, d1
007540:  c240                 and.w    d0, d1
007542:  56ed1619             sne.b    $1619(a5)
007546:  670c                 beq.b    $7554
007548:  b23c0040             cmp.b    #$40, d1
00754c:  660003e4             bne.w    $7932
007550:  0240000f             andi.w   #$f, d0
007554:  3c00                 move.w   d0, d6
```
### `$7450` - edge slope setup: per edge `(dx<<5)/dy` with `divs.w d3,d2`
```
sub_007450:
007450:  426d1604             clr.w    $1604(a5)
007454:  3018                 move.w   (a0)+, d0
007456:  3e00                 move.w   d0, d7
007458:  45faf696             lea.l    $6af0(pc), a2
00745c:  d4ed1604             adda.w   $1604(a5), a2
007460:  e948                 lsl.w    #$4, d0
007462:  d16d1604             add.w    d0, $1604(a5)
007466:  7a10                 moveq    #$10, d5
007468:  7c05                 moveq    #$5, d6
00746a:  7802                 moveq    #$2, d4
00746c:  5347                 subq.w   #$1, d7
00746e:  4240                 clr.w    d0
007470:  4242                 clr.w    d2
007472:  1018                 move.b   (a0)+, d0
007474:  1418                 move.b   (a0)+, d2
007476:  e968                 lsl.w    d4, d0
007478:  e96a                 lsl.w    d4, d2
00747a:  4cb100030000         movem.w  (a1, d0.w), d0-d1
007480:  4cb1000c2000         movem.w  (a1, d2.w), d2-d3
007486:  b641                 cmp.w    d1, d3
007488:  6e0a                 bgt.b    $7494
```
### `$7af0` - span fill handlers: planar 4-plane AND/OR-mask span writes (one routine per colour class; selected by self-modified words at $76ee/$79fc via $7a24)
```
sub_007af0:
007af0:  51cd0008             dbra     d5, $7afa
007af4:  c280                 and.l    d0, d1
007af6:  8682                 or.l     d2, d3
007af8:  6014                 bra.b    $7b0e
007afa:  8198                 or.l     d0, (a0)+
007afc:  c598                 and.l    d2, (a0)+
007afe:  70ff                 moveq    #$ff, d0
007b00:  51cd0004             dbra     d5, $7b06
007b04:  6008                 bra.b    $7b0e
007b06:  20c0                 move.l   d0, (a0)+
007b08:  4298                 clr.l    (a0)+
007b0a:  51cdfffa             dbra     d5, $7b06
007b0e:  8398                 or.l     d1, (a0)+
007b10:  c798                 and.l    d3, (a0)+
007b12:  4e75                 rts      
007b14:  51cd0008             dbra     d5, $7b1e
007b18:  c280                 and.l    d0, d1
007b1a:  8682                 or.l     d2, d3
007b1c:  6018                 bra.b    $7b36
007b1e:  c598                 and.l    d2, (a0)+
007b20:  8158                 or.w     d0, (a0)+
```
### `$5452` - vertex transform: 2D rotation by `muls`/`asr` (camera yaw/pitch matrix at $15a4)
```
sub_005452:
005452:  41ed15a4             lea.l    $15a4(a5), a0
005456:  4a2c0080             tst.b    $80(a4)
00545a:  6724                 beq.b    $5480
00545c:  3f02                 move.w   d2, -(a7)
00545e:  4ca800780010         movem.w  $10(a0), d3-d6
005464:  3f00                 move.w   d0, -(a7)
005466:  3401                 move.w   d1, d2
005468:  c5c4                 muls.w   d4, d2
00546a:  c1c6                 muls.w   d6, d0
00546c:  e6a2                 asr.l    d3, d2
00546e:  eaa0                 asr.l    d5, d0
005470:  d042                 add.w    d2, d0
005472:  341f                 move.w   (a7)+, d2
005474:  c3c6                 muls.w   d6, d1
005476:  c5c4                 muls.w   d4, d2
005478:  eaa1                 asr.l    d5, d1
00547a:  e6a2                 asr.l    d3, d2
00547c:  9242                 sub.w    d2, d1
00547e:  341f                 move.w   (a7)+, d2
005480:  4a2c007c             tst.b    $7c(a4)
005484:  6722                 beq.b    $54a8
```
### `$5268` - projection: x/(z+$100), y/(z+$100) with two `divs.w`, +$2e horizon bias
```
sub_005268:
005268:  2c2d158c             move.l   $158c(a5), d6
00526c:  6704                 beq.b    $5272
00526e:  610000e0             bsr.w    $5350  ; sub_005350
005272:  4245                 clr.w    d5
005274:  302c0074             move.w   $74(a4), d0
005278:  906d1590             sub.w    $1590(a5), d0
00527c:  6b02                 bmi.b    $5280
00527e:  3a00                 move.w   d0, d5
005280:  3945007a             move.w   d5, $7a(a4)
005284:  41fafd8a             lea.l    $5010(pc), a0
005288:  2248                 movea.l  a0, a1
00528a:  3e2d158a             move.w   $158a(a5), d7
00528e:  4c980007             movem.w  (a0)+, d0-d2
005292:  d245                 add.w    d5, d1
005294:  4441                 neg.w    d1
005296:  d26d000c             add.w    $c(a5), d1
00529a:  48c0                 ext.l    d0
00529c:  48c1                 ext.l    d1
00529e:  e188                 lsl.l    #$8, d0
0052a0:  e189                 lsl.l    #$8, d1
0052a2:  06420100             addi.w   #$100, d2
```
### `$c91a` - background template copy: `movem.l` 5x32 B per row from $7fac pointer into draw buffer $144(a5) (sky/ground)
```
sub_00c91a:
00c91a:  3c3c0020             move.w   #$20, d6
00c91e:  4cd80c3f             movem.l  (a0)+, d0-d5/a2-a3
00c922:  48d10c3f             movem.l  d0-d5/a2-a3, (a1)
00c926:  d2c6                 adda.w   d6, a1
00c928:  4cd80c3f             movem.l  (a0)+, d0-d5/a2-a3
00c92c:  48d10c3f             movem.l  d0-d5/a2-a3, (a1)
00c930:  d2c6                 adda.w   d6, a1
00c932:  4cd80c3f             movem.l  (a0)+, d0-d5/a2-a3
00c936:  48d10c3f             movem.l  d0-d5/a2-a3, (a1)
00c93a:  d2c6                 adda.w   d6, a1
00c93c:  4cd80c3f             movem.l  (a0)+, d0-d5/a2-a3
00c940:  48d10c3f             movem.l  d0-d5/a2-a3, (a1)
00c944:  d2c6                 adda.w   d6, a1
00c946:  4cd80c3f             movem.l  (a0)+, d0-d5/a2-a3
00c94a:  48d10c3f             movem.l  d0-d5/a2-a3, (a1)
00c94e:  d2c6                 adda.w   d6, a1
00c950:  51cfffcc             dbra     d7, $c91e
00c954:  4e75                 rts      

sub_00c956:
00c956:  4281                 clr.l    d1
```
### `$afc4` - IKBD byte send + fixed 200-iteration delay loop; called from the VBL handler for the joystick poll (cmd $16)
```
sub_00afc4:
00afc4:  102e7c00             move.b   $7c00(a6), d0
00afc8:  08000001             btst.b   #$1, d0
00afcc:  67f6                 beq.b    $afc4  ; sub_00afc4
00afce:  303c00c8             move.w   #$c8, d0
00afd2:  4e71                 nop      
00afd4:  51c8fffc             dbra     d0, $afd2
00afd8:  1d587c02             move.b   (a0)+, $7c02(a6)
00afdc:  4e75                 rts      
00afde:  48e7fff8             movem.l  d0-d7/a0-a4, -(a7)
00afe2:  142e7c00             move.b   $7c00(a6), d2
00afe6:  6a0e                 bpl.b    $aff6
00afe8:  08020000             btst.b   #$0, d2
00afec:  6708                 beq.b    $aff6
00afee:  4240                 clr.w    d0
00aff0:  4ef801ae             jmp      $1ae.w
00aff4:  6128                 bsr.b    $b01e  ; sub_00b01e
00aff6:  082e00047a01         btst.b   #$4, $7a01(a6)
00affc:  67e4                 beq.b    $afe2
00affe:  08ae00067a11         bclr.b   #$6, $7a11(a6)
00b004:  4cdf1fff             movem.l  (a7)+, d0-d7/a0-a4

```
### `$c84a` - ground/water dither fill: $aaaa/$5555 pattern rows below the horizon via `movem.l`
```
sub_00c84a:
00c84a:  286d0144             movea.l  $144(a5), a4
00c84e:  d9ed01a2             adda.l   $1a2(a5), a4
00c852:  383c008b             move.w   #$8b, d4
00c856:  986d1544             sub.w    $1544(a5), d4
00c85a:  6b4c                 bmi.b    $c8a8
00c85c:  203caaaaaaaa         move.l   #$aaaaaaaa, d0
00c862:  2200                 move.l   d0, d1
00c864:  2040                 movea.l  d0, a0
00c866:  2241                 movea.l  d1, a1
00c868:  243c55555555         move.l   #$55555555, d2
00c86e:  2602                 move.l   d2, d3
00c870:  2442                 movea.l  d2, a2
00c872:  2643                 movea.l  d3, a3
00c874:  48e4c0c0             movem.l  d0-d1/a0-a1, -(a4)
00c878:  48e4c0c0             movem.l  d0-d1/a0-a1, -(a4)
00c87c:  48e4c0c0             movem.l  d0-d1/a0-a1, -(a4)
00c880:  48e4c0c0             movem.l  d0-d1/a0-a1, -(a4)
00c884:  48e4c0c0             movem.l  d0-d1/a0-a1, -(a4)
00c888:  48e4c0c0             movem.l  d0-d1/a0-a1, -(a4)
00c88c:  48e4c0c0             movem.l  d0-d1/a0-a1, -(a4)

```

Also seen: `$aaa2`: `tst.b $1a6(a5)/bpl` spin until the VBL handler's per-frame counter ($1a7 = minimum VBLs per frame) expires, then `bset #3,$8f(a5)/bne` spin until the next VBL clears the bit (`$c616`): the flip is VBL-locked; these loops are idle time, not work.
`$7a24` writes two words into the code (`move.w $7a3c(pc,d0.w),$76ee.l`, `$79fc.l`): **self-modifying code** picks the span routine per colour class.
`$10f52` is a byte-pattern search (`rol.l #8,d0 / cmp.b (a0)+,d1 / bne`), ~1.6-2 % of cycles with no static caller found [INFERENCE: a record scan in a loaded data file].

## 4. Damocles/Mercenary-like features (from the code above)
- Flat-shaded polygons, edge-table scan converter: `$7450` stores per edge {x0,y0,dy,slope} (slope = `(dx<<5)/dy` by `divs.w`, `$7450..$74b6`), `$7518` finds the vertical extent (clamped to the $8c = 140-row window, `cmp.w #$8c`), walks the left/right edge pair per scanline with 16.16-ish accumulators (`lsl.l #5`) and calls span routines.
- Span-based filler with planar AND/OR masks (`$7af0..`): `or.l d0,(a0)+ / and.l d2,(a0)+` writes the 4 planes of 16-pixel groups with edge masks; `moveq #-1`/`clr.l` fill runs in the middle. Not a line filler, not a blitter use.
- No depth sort routine found in the top-15 (painter ordering is probably done in the scene walk `$3ada`; [INFERENCE]).
- Terrain is a grid of cells (`$3ada`: `move.w #$1900,d5`, `moveq #7,d7` loop; heights 0..~280 at world coords /256; island ~20x18 cells).
- Dither water/ground rows below the horizon are a constant pattern filled by `$c84a` (`move.l #$aaaaaaaa,d0` / `#$55555555,d2`, `movem.l` stores), height from `$8b - $1544(a5)`.

## 5. Wasted work (evidence + [INFERENCE] where not proven)
Repeated per frame:
- Background template copy `$c90e/$c91a`: 600 `movem.l` pairs per frame = {47.6k} cycles/frame (2.7-4.2 %). It copies a constant template into the draw buffer, then `$c84a` (2-3.4 %) fills the dither rows again over it: two full-width passes over the same rows. [INFERENCE] part of both is overwritten by terrain/sea polygons (overdraw), not counted.
- IKBD joystick interrogate in the VBL handler (`$c5fa moveq #$16,d0 / bsr $afbe`) with a 200-iteration `dbra` delay after the TDRE wait: `$afc4`+`$afd2/$afd4` = 2.4 % of all cycles at every frame rate (8.5 calls/frame x 3,855 cycles). The extra delay loop is a pure wait; a TDRE-only wait would save ~2 % pixel-identically [INFERENCE: timing hazard only if the IKBD needs the gap; the gap is >> the ACIA byte time].
- Standing still: the scene is re-rendered in full every frame (1.76 M cycles, `$3990` = 88 %) although only birds/NPCs move; a static-frame skip would not be pixel-identical while the NPC soldier or seagulls move [INFERENCE: skip only when the object list is unchanged for 2 frames].
- `$7a24` rewrites the self-modified words on every polygon (115 calls/frame in stand): cheap (226 cycles/call, 1.95 %), could be skipped when the colour class repeats.
Overdraw: NOT measured (would need span-write counting, e.g. a breakpoint trace on `$7af0` entries x widths); no number is claimed.
Hidden polygons: polygons entirely below row $8c are rejected early in `$7518` (`$75bc..$75c6`: `cmp.w #$8c,d2 / blt / st.b $1618(a5) / rts`, `bmi $75c2`), so HUD-covered geometry costs only the edge setup `$7450`; polygons partly above are clipped by row range only. Back-face handling: not found [INFERENCE]. Off-screen horizontal clipping: not located in the top functions.
Integrity/debug code: START.TOS has a sector checksum (`$f9a8`) at load time only; nothing per frame found.

## 6. Maths (mul/div in the hot paths; counts per frame from `profile counts`, instruction classes from the dump)
| class | foot_stand | foot_walk | car_drive | where |
|---|---:|---:|---:|---|
| `divs` | 926/frame, 7.8 % cycles | 622, 6.8 % | 553, 7.2 % | `$7450` 392 (edge slope `divs.w d3,d2`), `$5268` 358 (projection, 2 per vertex), `$3ada` 151, `$368a` 18 |
| `divu` | 28 (0.2 %) | 21 | 23 | `$10f52`, `$c4cc` |
| `muls` | 877, 2.7 % | 210, 0.9 % | 754, 3.7 % | `$5452` 756 / `$54f4` 67 (rotation) |
| `mulu` | 144 (0.4 %) | 93 | 86 | `$7518` 105 |
Divisors: edge slope = integer dy (1..140): a reciprocal table gives the exact result only if a correction step re-checks the remainder; replacement is NOT pixel-identical without that step (truncation) [INFERENCE]. Projection divisor `z+$100` varies per vertex: no constant. The camera matrix (`$15a4`/`$15bc`) is constant within a frame: the rotation `muls` are per vertex and cannot move to per-object unless objects are pre-transformed; they could be skipped for vertices shared between polygons (cached transform) [INFERENCE]. Trig: no sin/cos computed per frame found in the top-15 (matrix looked up/precomputed; `$15a4`) [INFERENCE].

## 7. Blitter
| candidate | CPU cost | verdict |
|---|---|---|
| template copy `$c91a` (movem 32 B per 12+8*... , 160 B/row) | ~47.6k cycles for ~20 KB per frame = ~2.3 cycles/B | no: at the `movem` limit (STE blitter ~2 cycles/B + setup, and the CPU would be stalled) |
| dither fill `$c84a` | `movem` stores of a constant pattern, similar ~2.2 cycles/B | no (MW2: blitter sky fill saved 0.15 %) |
| screen clear `$c8c0` (1.1-1.7 %) | `movem.l d0-d3/a0-a3,-(a4)` | no: same rate; could be dropped if the template copy covers the rows (overdraw of a clear by a copy) [INFERENCE] |
| span fills `$7af0` | short runs (AND/OR masks per 16 px, per-polygon), `or.l/and.l` pairs | no: runs are short and masked per word; blitter set-up per span exceeds the saving |
| HUD redraw | only changed gauges per frame; not in the top-15 | not applicable |

## 8. Ranked pixel-identical optimisation opportunities (all estimates [INFERENCE])
| # | idea | est. | risk |
|---|---|---:|---|
| 1 | Edge walk `$7518` (38 %): hoist loop invariants, `movem`/register-resident accumulators, remove per-scanline re-loads of `$1606(a5)` etc.; unroll the inner edge-step | 5-10 % of frame | medium (large routine, self-modifying parts) |
| 2 | Span fill handlers `$7af0..`: avoid re-evaluating masks per span when the span is within one 16 px group; use `movem` for wide runs | 2-4 % | medium |
| 3 | Edge setup `$7450`: replace `divs.w d3,d2` by exact reciprocal table + remainder fix-up; skip degenerate/horizontal edges | 2-4 % | medium-high (must be exact) |
| 4 | Remove the 200-iteration IKBD delay in the VBL handler (`$afc4`) | ~2 % | low-medium |
| 5 | Merge `$c91a` template copy with the `$c84a` dither fill (write each row once) | 2-3 % | low |
| 6 | Cache vertex transforms (`$5452/$54f4` muls) for vertices shared by polygons | 1-3 % | medium |
| 7 | Skip `$7a24` when the colour class is unchanged | 0.5-1 % | low |
| 8 | Quantisation: because frames are whole VBLs, shaving ~1 % off the stand view (11.0 VBL) yields 10 VBL = +10 % fps there | up to +10 % fps in specific views | n/a |
| 9 | Static-frame skip when nothing in view changes | large when it applies | high (NPCs/birds animate) |
