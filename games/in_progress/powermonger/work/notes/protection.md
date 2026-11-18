# Powermonger: the copy-protection question, how it works, and why `pm_noprot` removes it completely

Tags: **[obs]** observed in Hatari 2.6.1 (raw output quoted); **[disasm]** read from `work/dumps/entry10a6.bin` (the stage 2 image at the `$10A6` hand-over, bit-identical to `DATA\SPRITE40.DAT` depacked + relocated) with `tools/m68dis.py`; **[INFERENCE]** not verified.
Addresses are stage 2 addresses (position dependent, the same on every machine/TOS/RAM size). Patches: `patches/pm_noprot.s` (site `$14e4e`) and `patches/pm_noprot_box.s` (site `$bee0`), both stage 2, `; default: yes`.

## 1. Result in one paragraph
The "protection" is not a disk check and not a one-off question. The state "protection passed" is **one long word at `$14e4e`** (`$0000002c`). Until it holds `$2c`, the first time the renderer reaches the sprite handler at `$11bf4` (the handler of a person in state `$0e`: person #32 is in state `$0e` before and after) it runs the check: it builds a decoy random land, asks "how many Houses/People in this land?" (answer = the game's own object count of that decoy land), and compares. A right answer writes `$2c` into `$14e4e` and rebuilds the real land; a wrong answer leaves `$14e4e = 0`, prints "Demo mode now activated" and **the game goes on in the decoy land with Save/Format disabled**. The patch presets `$14e4e = $2c` at the game's hand-over (`$10A6`) and does not open the "Please Wait For The Protection Check" box. The check can then never start, and every other reader of the word sees exactly what it sees after a correct answer. **No second hidden check exists** (section 5).

## 2. Where everything is [disasm]

| address | what |
|---|---|
| `$14e4e` (long) | **the pass flag**. Original content `6000 1374` = `bra.w $161c4`: the word lies inside the people-state jump table (`$14bac: move.w $14bb4(pc,d0.w),d0 / jmp $14bb4(pc,d0.w)`), in a run of identical `bra.w $161c4` slots (`$14e4a`, `$14e4e`, `$14e52`: `6000 1378 / 6000 1374 / 6000 1370`). `$0000002c` there is `ori.b #$2c,d0` and falls through into the next `bra.w $161c4`; `$00000000` (failure) is `ori.b #0,d0`. The check reads it as a byte (`$60`) and as a long (`$2c`). |
| `$11bf4` | sprite-frame handler of people state `$0e` [INFERENCE: the state is deduced from the `move.b #$e,$6(a3)` it ends the check with and from person #32 being in state `$0e` in every dump]. **The trigger** (listing 3.1). |
| `$95f6` | click-on-person dispatcher. `jsr $9624(pc,d0.w)`, `d0 = $6(a3)` = person state; state `$2e` -> table word `$1cb0` -> `$b2d4`. |
| `$b2d4`..`$b470` | the decoy land + question box setup (listing 3.2). |
| `$b440`/`$b44e`..`$b470`, `$b472`.., `$b4d0` | the question box (text at `$b510`: "Between Pages @@@@@ ..."; `$b4d0` picks the noun "Houses"/"People" from `$57ff8`; `$b472` formats the page range from `$5809c`). |
| `$b892` | counts the decoy land's objects into `$5878c..$58795` (6 words: captains `$4e514` stride `$20`, houses `$4f916` stride `$12`, people `$51b66` stride `$32`, ...). |
| `$b814` | **the answer check**, called from the UI dispatcher at `$7890` when button `$2a3`/`$2b1` (OK) is clicked (listing 3.3). |
| `$b9ac` | wrong-answer message box ("Your answer is wrong You Have been deemed unworthy to rule this fair land. Demo mode now activated."). |
| `$bee0` | the "Please Wait For The Protection Check" box (text at `$bf12`), called only from `$12fd2` (the new-conquest start, right after `jsr $13b9a` and `move.w #1,$1c48a`). |
| `$13b9a` | the real game start (clears the state area `$3f364..$57ff8`, loads/generates the land, draws it). `$12f9c` and `$13d1a` call it, and so does the success path. |

### 3.1 The trigger: the `$11bf4` handler [disasm]
```
011bf4:  6100031c       bsr.w    $11f12
011bf8:  41f900014d12   lea.l    $14d12.l, a0
011bfe:  0c280060013c   cmpi.b   #$60, $13c(a0)        ; byte at $14d12+$13c = $14e4e : still the original `bra.w` opcode?
011c04:  6624           bne.b    $11c2a                ; no (flag set / failed before): normal sprite frame only
011c06:  177c002a0006   move.b   #$2a, $6(a3)          ; state := $2a + 4 = $2e (written as a sum so the constant does not show)
011c0c:  062b00040006   addi.b   #$4, $6(a3)
011c12:  33fc00010002df96 move.w #$1, $2df96.l         ; fake a click
011c1a:  41f90000957e   lea.l    $957e.l, a0
011c20:  4ea80078       jsr      $78(a0)               ; = jsr $95f6 -> state $2e -> $b2d4 (the check)
011c24:  177c000e0006   move.b   #$e, $6(a3)           ; the person goes back to state $0e
011c2a:  142b0005       move.b   $5(a3), d2            ; (the handler's real job: sprite frame $13e+dir)
011c2e:  4882           ext.w    d2
011c30:  0642013e       addi.w   #$13e, d2
011c34:  4e75           rts
```
So the check is armed by the state of the program image itself, not by a variable, and it fires from inside the 3D renderer: the very first frame of any new conquest (and of any other start path that draws a person of that state, since the test is the same [INFERENCE: continue conquest not run on the unpatched disk]). [obs] (cold boot, breakpoint `pc = $b2d4`): the call comes from `$9616: jsr $9624(pc,d0.w)`: stack top `0000961a`, saved regs d1 = `$2e`, `a3 = $521a6` = person #32 (`$51b66 + 32*$32`), whose state byte is `$0e` afterwards.

### 3.2 The decoy land and the question (`$b2d4`, abridged) [disasm]
```
00b2d4:  33fc00a00002c1be  move.w #$a0, $2c1be.l
00b2dc:  4bf9000584c4      lea.l $584c4.l, a5            ; BACKUP: the real land's state $580a0..$58367 -> $584c4
00b2e2:  43f9000580a0      lea.l $580a0.l, a1
00b2e8:  3ad9              move.w (a1)+, (a5)+
00b2ea:  b3fc00058368      cmpa.l #$58368, a1
00b2f0:  66f6              bne.b $b2e8
00b2f2:  13f900ff8209000580a3 move.b $ff8209.l, $580a3.l   ; decoy seed = video counter + $2df92 + $6f304 (VBL count) + RNG ...
 ...                                                       ; $580a0 = seed*11+$3fb, $5809c = (seed mod $90)*$96+$672  (decoy "page" numbers)
00b380:  4eb90000fe04      jsr $fe04.l                    ; the same init calls as $13b9a: land generation from the decoy seed
00b386:  4eb900010768      jsr $10768.l                   ; clears the game state $3f364..$57ff8
00b394:  4eb900010d1e      jsr $10d1e.l                   ; land from seed ($5809c != 0)
  ...
00b3d0:  4eb90000b892      jsr $b892.l                    ; count the decoy's objects -> $5878c..
  ...
00b40e:  33fc00000002c1be  move.w #$0, $2c1be.l
00b416:  d0b90002df92      add.l $2df92.l, d0 ; add.w $6f306.l, d0 ; andi.w #1, d0 ; cmp.w #2,d0 ...
00b430:  33c000057ff8      move.w d0, $57ff8.l            ; question type 0 = Houses, 1 = People   (RNG bit)
00b436:  23fc0000000000014e4e move.l #$0, $14e4e.l        ; <<< the flag is CLEARED (a hit of the check always starts from "failed")
00b440:  4eb90000abcc      jsr $abcc.l                    ; closes the "Please Wait" box (abcc clears the box state words $7a36..)
00b446:  33fc000000007a38  move.w #$0, $7a38.l
00b44e:  43f90000b510      lea.l $b510.l, a1              ; open the question box ...
00b454:  4eb900007b10      jsr $7b10.l
...
00b470:  4e75              rts
```
The decoy overwrote the whole game (state, land, screen), which is why the success path has to restore and rebuild everything.

### 3.3 The check [disasm]
```
00b814:  48e7fffe             movem.l d0-d7/a0-a6,-(a7)
00b818:  41f900007a36 ...     lea $7a36.l,a0 ; adda ... ; jsr $b940.l        ; parse the typed 4-digit number -> d0
00b82e:  41f90005878e         lea.l $5878e.l, a0                             ; expected answers (houses at +0, people at +2 ...)
00b834:  323900057ff8         move.w $57ff8.l, d1 ; add.w d1,d1
00b83c:  4eb90000abcc         jsr $abcc.l                                    ; close the question box
00b842:  90701000             sub.w (a0,d1.w), d0
00b846:  663e                 bne.b $b886                                    ; wrong -> failure
; ---- success --------------------------------------------------------------------------------------
00b848:  48c0                 ext.l d0                                       ; d0 = 0
00b84a:  06800000002c         addi.l #$2c, d0                                ; $2c
00b850:  41f900014c0c         lea.l $14c0c.l, a0
00b856:  21400242             move.l d0, $242(a0)                            ; $14c0c+$242 = $14e4e := $0000002c    <<< THE FLAG
00b85a:  42790005809c         clr.w $5809c.l                                 ; page number back to 0
00b860:  4bf9000584c4         lea.l $584c4.l, a5                             ; restore the real land's state from the backup
00b866:  43f9000580a0         lea.l $580a0.l, a1
00b86c:  32dd                 move.w (a5)+, (a1)+
00b86e:  b3fc00058368         cmpa.l #$58368, a1
00b874:  66f6                 bne.b $b86c
00b876:  4eb900013b9a         jsr $13b9a.l                                   ; rebuild the real game
00b87c:  33fc00010001c48a     move.w #$1, $1c48a.l
00b884:  6006                 bra.b $b88c
; ---- failure --------------------------------------------------------------------------------------
00b886:  4eb90000b9ac         jsr $b9ac.l                                    ; "Your answer is wrong ... Demo mode now activated."
00b88c:  4cdf7fff             movem.l (a7)+, d0-d7/a0-a6
00b890:  4e75                 rts
```
The success path's only lasting differences from a start that never asked are: the flag word, `$5809c = 0` and the restored state (`$580a0..` was never touched when no decoy is built). `$13b9a` ends by re-initialising every variable the decoy had set (`$ff9a`, `$57fee`, `$57ff0`, `$2df96`, `$2c1be`, `$57ffc`, ...; compare `$b3d6..$b3f0` with `$13c9c..$13cb4`), so it is a full restart, equal to the first start that `$12fc6` already did.

## 4. Failure consequence (experiment, unpatched disk) [obs]
Cold boot of `disks/protected.st`, START NEW CONQUEST, island, question; OK pressed with 0000 (script `fail.py`, screenshot `work/shots/prot_wrong_answer_demo.png`):
```
question type 0 expected 108 flag before 0x0 w5809c 0x1518 l580a0 0x50e
after OK: flag 0x0 w5809c 0x1518 l580a0 0x50e iter 114
iter 208 -> 388 flag 0x0
```
* The game does **not** end. The message box "Your answer is wrong You Have been deemed unworthy to rule this fair land. Demo mode now activated." stays on screen, the main loop keeps iterating (iteration 208 -> 388 in 20 s), and you play **in the decoy land** (a different, mostly water island on the overview map; `$580a0 = $50e`, `$5809c = $1518` stay, the real land is never restored, `$13b9a` is not called).
* `$14e4e` stays 0 (`ori.b #0,d0`): the Save/Format/continue gating below stays in its "demo" state, and since the byte is no longer `$60` the check does not start again.

### 4.1 Everything that reads the flag [disasm]
Complete list from byte scans of the whole stage 2 image for the 32-bit values `$14e4e`, `$14d12`, `$14c0c`, and for PC-relative references into `$14b00..$14e6f` (none except the `$14bb4` jump table):

| site | test | meaning |
|---|---|---|
| `$11bfe` | `cmpi.b #$60,$13c($14d12)` | trigger of the check (3.1) |
| `$7774` | `cmpi.l #$2c,$14e4e` ... `bne $77be` | the UI buttons `$47` (`$e288`) and `$77` (`$1ba72` = the save-game disk code) only work when passed |
| `$af10`, `$af2a` | `cmpi.l #$2c,$14e4e` | picks the labels: `$af3e` "SAVE" / `$af43` "FORMAT" when passed, blanks (`$af4a`) otherwise |
| `$13ea6` (table `$13e8e`, entry 4 of `$2df6e`) | `cmpi.l #$2c,$14e4e ; beq $13ec0` | passed: straight to `$1120e / clr.l $580a0`; not passed: runs the dialog loop `$aeac / $cee6` first [INFERENCE: the save-disk dialog] |
| `$b436` / `$b856` | writes | clear / set |

So **demo mode = no saving or formatting of save disks**; there is no timer, no counter, no later re-check and nothing that re-clears the word (the only writers are `$b436` and `$b856`, both inside the check).

## 5. Why a static preset is exactly "after a correct answer"
[obs] RAM at the map view: the original flow's dump `work/dumps/map_idle.bin` (correct answer typed) holds `$14e4e = 0000 002c` and `$14e4e..$14e55 = 0000 002c 6000 1370`; the patched floppy's map view holds the same bytes (`xxd -s 0x14e40`). People states `$6(a3)`: 486 persons state 0 and 26 persons state `$0e` in both dumps (iteration 29 vs 31); person #32 (the one that triggers the check) is byte-identical in both (`...0e40290a32ce...`); the only 20 of the 512 person records differ at all: 14 only in byte 19, 6 (#2, 3, 13, 15, 16, 20) also in bytes 9-13, 17 and 41, all of them the moving/iteration-dependent fields, never the state byte; the rest are screen and variable areas that depend on the iteration. Nothing else the success path sets survives it: `$5809c` and `$580a0` are 0 in the patched run (`w5809c 0x0 l580a0 0x0`, as the success path leaves them), `$1c48a = 1` is set by `$12fca`.

The patch has two sites because `pmpatch.py` supports one site per patch file:
* `pm_noprot.s`: `$14e4e` `60001374` -> `0000002c`. Static, so it covers every start path (new conquest, continue, random land) and every reader.
* `pm_noprot_box.s`: `$bee0` `43f90000bef6` -> `4e75 4e71 4e71` (`rts` + padding). The box would otherwise stay on screen forever: its only closer is `abcc` inside the check. Skipping it leaves the box state words `$7a36..` at 0, as after `abcc`.

## 6. Verification [obs]
`pmpatch.py build --floppy` (defaults: tick, snd, p4, noprot; 16 sites, free on disk 53248 B), cold boot with `pm.py boot_to_game` (which now detects `protection_removed()` = `peekl($14e4e) == $2c` before the island click and fails if the question box appears), breakpoints armed on `pc = $b2d4/$b440/$b814/$b9ac/$bee0`:

| machine | result |
|---|---|
| STE, TOS 1.62, 1 MB (`--only pm_noprot pm_noprot_box` build, 1st run) | `[123s] protection removed ... [141s] 3D map view`, `BOOT OK flag 0x2c MARKER b'PMPO' FLAGS 0x3 w5809c 0x0 l580a0 0x0 iter 30`, `get_men moving 17`, iteration 375, hit list `['pc = $bee0']` (the `rts` stub), screenshots `work/shots/prot_removed_mapview.png` |
| STE, TOS 1.62, 1 MB (default build) | `BOOT OK ... iter 51`, `moving people: 15`, iteration 313, hits `['pc = $bee0']` |
| ST, TOS 1.04, 1 MB (default build) | `BOOT OK flag 0x2c MARKER b'PMPO' FLAGS 0x6 ...`, `get_men moving 15`, iteration 310, hits `['pc = $bee0']` |
| STE, TOS 1.62, 1 MB, default build, **play-on** | get_men (15 moving), then about 270 s of play after the map view (map view at 142 s, last poll at 411 s): iteration `295 / 431 / 567 / 702 / 837 / 972 / 1108`, final `1126`; every poll `flag 0x2c hud True`; the seasons change (tree colours, `work/shots/prot_removed_it1100.png`); no `b2d4 / b814 / b9ac` hit, no demo message, no defeat screen by iteration 1126 |
Original unpatched flow for comparison (same harness): chart `[112s]` -> question `[149s]` -> answer -> map view `[196s]`; patched: chart `[113s]` -> map view `[141s]`, i.e. about 55 s less, and no extra clicks.

## 7. What the crack changed (WAR.DAT, `replicants_t2`) [disasm]
`cmp -l` (1-based offsets, octal values) shows 4 differences between `AUTO/WAR.PRG` and `replicants_t2/AUTO/WAR.DAT`: file offsets 39, 41, 516, 517 (0-based; text offsets `$b, $d, $1e8, $1e9`).
* Text `$8..`: `lea $8240.w,a0 / moveq #15,d0 / clr.w (a0)+ / dbra` (blank the palette) becomes `lea $8244.w / moveq #13`: colours 0 and 1 stay as the crack's own intro left them.
* Text `$1e4..$1e9`: `move.l #$005c4e75,-(a7)` becomes `move.l #$005c4afc,-(a7)`: the last two instructions of the 32-byte stack routine that jumps into the depacked stage 1 are `lea $5c(a7),a7 / rts`; the crack makes the `rts` an **`illegal`** (`$4afc`), i.e. the crack's loader (`AUTO/INTRO.PRG`, "Automation Packer V2.3r", packed, not decoded here) takes the exception to patch the freshly unpacked game before it runs, exactly the place our `hook1`/`hook2` use (`jmp hook` instead of `rts`).
So the crackers did the same job as `pm_noprot` (patch after unpack); the actual protection patch is inside the packed INTRO.PRG. Two attempts to boot `replicants_t2.st` in Hatari (1 MB STE, TOS 1.62) did not reach the game's name prompt in 400 s (first: stuck on its trainer menu "WIN EACH TIME ? (Y/N)"; second: after pressing `n` the screen stayed black), so what exactly it patched was not recovered; **it is not needed**, because the semantics were derived from the game code above and the result was proven by the cold boots in section 6. [INFERENCE] a crack would most simply preset the same word, or patch `$11c04` `bne` to `bra`.

## 8. Reproduce
```
cd games/in_progress/powermonger
python3 tools/pmpatch.py verify                       # `ok pm_noprot` / `ok pm_noprot_box`: derived origs match
python3 tools/pmpatch.py build --floppy               # defaults include both
python3 tools/pmpatch.py boot --disk build/floppy/powermonger.st [--machine st --tos 1.04] --peek 14e4e:4 --peek bee0:6
```
Expected: `BOOT OK ... in_game=True MARKER=b'PMPO'`, `peek $14e4e: 0000002c`, `peek $bee0: 4e754e714e71`.
