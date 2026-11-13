# Populous 2: low-RAM floppy build on the ICS crack (`pop2patch.py build --base ics`)

2026-11-13. Hatari 2.6.1, headless, audio off. Disk: `alt/ST/Populous II (1991)(Bullfrog)[cr ICS][512 kB].st` (never modified; the build copies it). Output `build/ics/Populous2_lowram.st`.
Scripts (scratch, kept): `work/scratch/ics/` (`memmap.py` stock pattern test, `memmap2.py` patched pattern test, `cell.py` cold-boot cell, `saves3.py`, `boot1.py`). Raw logs: `work/gates/ics_*.log`, `ics_stock_pattern_*.txt`.

## 0. Verdict

| item | result |
|---|---|
| 512 KB (ST TOS 1.04, STE TOS 1.62) | **plays**, all default patches except the plain-ST sprite cache; in-game save/load on the game disk |
| 1 MB (STE TOS 1.62, ST TOS 1.04) | **plays**, the full PP layout (including the sprite cache) |
| Mega STE TOS 2.06 4 MB, 60 Hz (PP's floppy fails here) | **plays** (6.230 turns/s at 60 Hz), save/load OK |
| Falcon TOS 4.04 4 MB (Hatari, 16 MHz) | **plays** (6.262/s), save/load OK (the crack's cracktro hung here; our boot does not run it) |
| TT TOS 3.06 `--mmu true` | 8 MHz (`--cpuclock 8`): **plays** (6.230/s at 60 Hz). 32 MHz (default): the game's own floppy routine fails, "INSERT POPULOUS-II DISK" forever, no crash (section 7) |
| in-game saves | 3 of 56,690 B fit (172,032 B needed, 177,152 free); the ICS disk had 175,104 (also 3) |
| fixed rate | 6.23-6.26 turns/s on every machine that plays |

## 1. The ICS boot chain (disassembled / measured)

```
TOS (AUTO folder)  AUTO\ICS.PRG   cracktro, packed; leaves a 10-byte stub at $140:  23fc 4e714e71 00014a88 / 4ef8 1770   (dump, ics_at140.bin $140)
                   AUTO\LOADER.PRG  157 B: Mshrink, Pexec("credits.tos"), Pexec("pop2.tos", " 1")
CREDITS.TOS        Bullfrog credits
POP2.TOS (94,488 B text, no relocs, 140 B symbols)
  text $00-$15  clr.l -(a7) / move.w #$20,-(a7) / trap #1 / moveq #0,d0 / moveq #7,d1 / lea $8240.w,a0 / move.l d0,(a0)+ / dbra   (Super, palette black)
  text $16      move.w #$2700,sr ; lea $167e.w,a1 ; copy the decruncher (text $36..$127) there ; jmp $167e
  $167e         copy the packed block (text $128, $16ff0 B) to $1770, decrunch it in place (Atomik-style, text $56-$126) -> 498,704 B = $1770-$7b380
  text $4e      lea $1770.w,a7 / jmp $140.w
```
`pop2patch.py` carries a Python port of that decruncher (`atomik_depack`, checksum checked). `verify --base ics` output:
```
unpack (atomik_depack, checksum 0): 498704 bytes; vs RAM dump at `jmp $140` ics_at140.bin: 0 of 498704 differ  (match)
the crack's $140 stub in the dump: 23fc4e714e7100014a884ef81770 = move.l #$4e714e71,$14a88.l / jmp $1770.w  (match)
```
So the ICS game = PP's P2M.FIC image (disks.md), and every patch site of the PP build is valid unchanged; the only crack patch on the image is `$14a88 := 4e714e71`
(two nops behind `cmp.w d1,d2` at $14a86, the manual question). PP's four RAM patches (`$1cf8 $14a88 $2cc98 $36efc`) are not on this base.

## 2. Memory map (proof by pattern fill and by the load table)

Stock ICS game; at `pc = $140` the debugger loads `A*2654435761+$1234567` into every long of the range, then a full session is played; the range is dumped and compared
after each step (`work/scratch/ics/memmap.py`; raw: `work/gates/ics_stock_pattern_1mb.txt`, `..._512kb.txt`):

```
[mm1m]  1 MB STE  $7b380-$100000: menu 0 changed, play 0, busy (11,144 turns, fast-forward) 0, effects (F1-F6, all slots, clicks) 0,
        save+load (turn 11906 -> 11923) 0, restart map 0, conquest2 0, custom game 0           RESULT ALL INTACT
[mm512] 512 KB STE $7b380-$80000: menu, play, busy (10,366 turns), effects, save+load (11131 -> 11147), restart, conquest2, custom: 0 changed   RESULT ALL INTACT
```
Static check: the game's file table (`$2cdb6`, 0x30 B per entry: dest.l, mask.l, len.l, flag.w, name) and the file sizes / last-long unpacked sizes (Atomik trailers):
every data file loads and unpacks inside the image: BLOCK0-3/CONQUEST/ELEMENTS/DIF at `$47d28`, FACES `$523f4`, AWARDS/TITLE `$54c80`, HANDS `$5a144`, PANEL `$49880`,
S32-0.PAK `$69450` (unpacked end `$6f2b0`), END.PAK `$6945c` (raw end `$771b4`, unpacked end `$79880`), S16-0.PAK `$6f2b0` (unpacked end **`$7b380`**, exactly the image end).
FX.DAT/QAZ.PAK have dest 0 (caller-supplied buffer; covered by the pattern runs). **Nothing the game loads or unpacks reaches `$7b380`.**

Memory map (TOS gone after the unpack; the game never calls it; the disk layer is the game's own FAT12 + raw WD1772 driver `$36efc`/`$375e0`):

| range | use |
|---|---|
| `$0-$13f` vectors; the game sets `$70`, `$102-$13f` (MFP), `$118` | |
| `$140` | the crack's stub (10 B); ours: `jmp CORE.l` |
| `$400-$1770` | TOS variables, mostly untouched by the game (RAM dump diff at menu: only `$43e`, `$465`, `$4bc`, `$a3f`, `$cdb-$ce4`, `$d75-$de0`, `$ea8`, `$ee4`, `$1544-$15f8`); not used by us |
| `$1770-$7b380` | the game (code, data, 2 screens `$2300`/`$a000` inside it, the 56,690-byte save area `$39630-$473a2`, data file buffers) |
| **`$7b380-$7ffff` (19.6 KB)** | **free at 512 KB** (proven above) |
| `$7b380-$f7fff` | free at 1 MB; `$f8000-$fffff` = TOS's screen, also never touched (pattern covered it) |

## 3. Delivery (`pop2patch.py build --base ics`)

* `AUTO\ICS.PRG` is deleted (it only left the stub; it hangs a Falcon, section 7 of disks.md), the rest of the disk is untouched (LOADER, CREDITS, the 28 data files).
* `POP2.TOS` is replaced by `prefix + LZ(payload_full + payload_lowram) + the crack's POP2.TOS` (the crack's text unchanged: its `lea d(pc)` are self-relative; its 140-byte
  symbol table is dropped to save a cluster). Header text length updated.
* The prefix (vasm, `ICS_PREFIX`): replays text `$0-$15` (checked byte for byte), unpacks the LZ stream (RUNME's own LZ format, `lz_unpack`; `lz_pack` in the tool, round-trip asserted) to a
  scratch area 256 B behind the end of its own text (a Pexec'd program owns all free RAM; the unpack comes later), picks the payload by `_phystop` (`$42e >= $100000` full, else lowram),
  writes `move.w #$4ef9,$140.w / move.l entry,$142.w`, zero-fills the layout's range, copies the non-zero chunks (payload format in the tool), `bra.w` to text `$16`.
  It runs before the unpack (which overwrites the TPA) and writes only `$140` and RAM >= `$7b400`.
* The trampoline `patches/core_ics.s` (entered by the crack's final `jmp $140.w` -> our `jmp`): does the crack's own `$14a88` store, verifies every site's original bytes (all or none), applies,
  marker `P2PO` / `P2PF` at `$7fff8`, `jmp $1770.w`. Same table format as `core.s`.
* `verify --base ics`: all 24 patch sites match the depacked ICS game and the RAM dump (0 mismatches); the PP path is unchanged (HD `RUNME.TOS` md5 `927e26ec...`, `live` image `f6609f93...`: identical before/after the refactor).

### Layouts
`full` (RAM >= 1 MB) = PP's layout, blobs byte-identical (PB = `$80000`, 32 KB image, data to `$8ffff`). `lowram` (512 KB) = the same sources placed by the tool into `$7b400-$7ec6f` (14,448 B incl. 6.1 KB of tick data):
patches that address each other through `PB` share one PB (`PB_FAMILY`), the `DB+` data blocks (pop2_ptr_a/b, pop2_spr; `DB = PB+$8000` in `full`) are placed apart, first-fit, `LITE` is defined for the sources
(pop2_spr: no pre-shifted cache). Free after the image: `$7ec70-$7fff7` = 4,992 B.
Changes in the sources: `PD`/`BLT`... use `DB+`; headers `; base: pp`, `; data: ... cache`; `pop2_spr.s` has `ifnd LITE` around the cache code. The PP builds are byte-identical afterwards.

### Patches not applied on the ICS build (header `; base: pp`)
`pop2_floppy_head` (HAGA's TOS-state swap), `pop2_save`, `pop2_save_w`, `pop2_save_d` (GEMDOS conversion of the disk layer; the ICS disk layer is intact and saves to A: itself). Everything else of the default set (20 patches) is applied.
`; base: ics` is also accepted by the tool; an experimental `pop2_fdc_delay` (section 7) was written and rejected (kept in `work/scratch/ics/rejected/`).

## 4. Feature vs RAM (code bytes / data bytes of the placed blobs, from the tool)

| feature (patches) | full (>= 1 MB) | lowram (512 KB) |
|---|---|---|
| core + site table (20 sites) | 128 + 684 | 128 + 684 (1 KB reserved) |
| fixed 6.25 turns/s tick, 50/60 Hz, command queue, sound step (`pop2_tick*`) | 910 / 6,144 | 910 / 6,144 |
| 60 Hz (`pop2_ntsc`, `pop2_ntsc2`), no manual question (`pop2_noquest`) | sites only | sites only |
| tooltips (`pop2_tooltip`) | 1,252 | 1,252 |
| pointer redraw skipping (`pop2_ptr_a/b`) | 508 / 512 | 508 / 512 |
| STE blitter sprites (`pop2_spr`, `pop2_spr16`, probe) | 620 / 4 | 620 / 4 |
| **plain-ST pre-shifted sprite cache** | 652 / 32,252 | **dropped** (the plain ST runs the original sprite code) |
| TT/Falcon pointer (`pop2_tt_ptr`), Falcon sound (`pop2_fal_ym`), mouse clamp, credit | 424+122+58+314 / 5 | same |
| total | 4,860 / 38,917 | 4,208 / 6,665 (14,448 B image) |

At 512 KB everything except the ST sprite cache fits with 4,992 B to spare; the tick's 5.4 KB minimap-dot list is the only data that could shrink further.

## 5. Disk budget (saves are the reason it matters)
ICS disk: 175,104 B free = 171 clusters = 3 saves (56 clusters each). Build: ICS.PRG removed (+7 clusters), POP2.TOS 94,660 -> 100,130 B (+7 clusters): 177,152 free = 173 clusters = 3 saves with 5 spare.
The payloads alone are 5,746 + 5,076 B; LZ-packed together 5,458 B (the two layouts share their code; packing each separately would cost one save). Without the LZ and the dropped symbol table the POP2.TOS grew to 105,646 B and only 2 saves fitted (measured during development).

## 6. Gates (all cold boots from the floppy; `cell.py`; logs `work/gates/ics_*.log`)

Cell = boot to the first conquest battle, marker, payload bytes in RAM vs the build's image (0 differ of ~4,100-4,700 non-zero bytes), turns/s over 1,500 VBL (Hatari fast-forward, per emulated second),
tooltip shots, in-game SAVE then LOAD, then quit and `mdir`/`fsck.fat` of the floppy image, log scan for bus/address errors.

| cell | layout | in play / marker | turns/s | save -> load | fsck | log errors |
|---|---|---|---|---|---|---|
| STE TOS 1.62 1 MB | full | yes / P2PO | 6.229 (160,168 cyc/VBL, 49.95 Hz) | turn 604 saved, 719 before load, **617** after; `T1.GAM` 56,690 | 35 files, 594/711 clusters | 0 |
| STE TOS 1.62 512 KB | lowram | yes / P2PO, `$22f14 = 4ef9 0007c780` | 6.229 | 621 -> 735 -> **635** (an earlier build of the same layout; the final prefix/payload was cold-booted on ST 512 KB above) | clean | 0 |
| ST TOS 1.04 1 MB | full | yes / P2PO | 6.262 | 731 -> 855 -> **744** | | 0 (1 = pop2_spr's blitter probe `$ffff8a28`, expected on an ST) |
| ST TOS 1.04 512 KB | lowram | yes / P2PO, `$22f14 = 4ef9 0007c780` | 6.229 (160,224 cyc/VBL) | 747 -> 864 -> **760** | 35 files, 594/711 | 0 |
| Mega STE TOS 2.06 4 MB, 60 Hz (sync `$fc`) | full | yes / P2PO | 6.263 (Hatari default 8 MHz: 133,557 cyc/VBL = 60 Hz; the tool's "NOT 60 Hz" flag is its 16 MHz assumption) | 614 -> 727 -> **627** | 35 files, 594/711 | 0 |
| Falcon TOS 4.04 4 MB | full | yes / P2PO | 6.262 (320,443 cyc/VBL, 49.93 Hz) | 581 -> 700 -> **597** | 35 files, 594/711 | 0 |
| TT TOS 3.06 `--mmu true`, `--cpuclock 8` | full | yes / P2PO | 6.230 (60 Hz) | not run | | 0 |
| TT TOS 3.06, 32 MHz | full | **no**: marker P2PO, game shows INSERT POPULOUS-II DISK | | | | 0 |

Raw lines (final build, `c_ste1m.log`, `c_fal404.log`):
```
CELL ste1m: ICS floppy ste TOS default 1024 KB (full layout); boot 114s in_play=True marker='P2PO' $22f14=4ef900082000 ... turn=100
payload $80000+32768: 4638 non-zero image bytes, 0 differ in RAM
RESULT ste1m default MHz 50 Hz: 1501 VBL = 30.02 s, 160168 cycles/VBL, world turns 187 = 6.229/s | ticks(D) 187 = 6.229/s; passes T 187 R 141 S 0 P 0 | refresh seen 49.95 Hz
SAVELOAD {'turn_at_req': 604, 'after_save_play': True, 'turn_before_load': 719, 'turn_after_load': 617, 'load_play': True}
disk after save: ['       34 files   586 836 bytes', '  119 808 bytes free'] ; GAM files ['T1  GAM  56690 1991-12-04  16:23 ']
fsck.fat -n: /tmp/ics_ste1m_a.st: 35 files, 594/711 clusters
RESULT fal404 default MHz 50 Hz: 1501 VBL = 30.02 s, 320443 cycles/VBL, world turns 188 = 6.262/s
SAVELOAD {'turn_at_req': 581, ... 'turn_before_load': 700, 'turn_after_load': 597, 'load_play': True}
```
The three-saves / disk-full / pattern-with-patches / `p2tick.py ab` / `p2abtest.py` gates: see section 8 (what was and was not run).

## 7. TT and Falcon
* **Falcon (Hatari TOS 4.04)**: plays. With the stock ICS disk only the cracktro hung (disks.md); the game and its raw FDC driver work here.
* **TT**: the game starts, our payload is in place (P2PO), then the first floppy read fails: "INSERT POPULOUS-II DISK" (`work/shots/ics_tt306_none.png`). The same disk at `--cpuclock 8` plays,
  so the failure depends on CPU speed [INFERENCE: the driver's WD1772 delay loop `$37a96` (`moveq #$18,d0 / subq.l / bne`, 54 us at 8 MHz) is too short on a 32 MHz 68030].
  That hypothesis was tested and NOT confirmed: a patch that multiplies the count by 24 on 68020+, one that does 6x with an I/O-bus read per iteration, and one with 128x (no I/O) all left the TT at 32 MHz
  failing (the code is in `work/scratch/ics/rejected/`; not shipped). The cause at 32 MHz is unresolved. No crash, no bus error in the log; the README says: TT at 8 MHz only, else use the HD version.
* real hardware: nothing here was run on real machines.

## 8. Snapshot gates on the relocated (lowram) layout, and the gap-closing pass
`P2_LAYOUT=ics-lowram` makes `p2abtest.py` / `p2tick.py` build the non-test patches with `pop2patch.py live --base ics --layout lowram` (the test_* walk patches stay at `$80000`; p2tick finds the tick block D from the json).
The PP snapshots (2 MB STE) carry the same game bytes, so they apply unchanged. First attempt of `ab busy1 8 130` had D computed from `pop2_tick` alone (R frames 0, 3 T frames differ): a harness bug (fixed, `p2tick.py` line 45).
Final, raw in `work/gates/ics_ab_lowram.txt`, `ics_abtest_lowram.txt`, `ics_abtest_lowram2.txt`:
```
p2tick.py ab: busy1 8/16 MHz, game_start 8/16 MHz, busy1 16 --hz 60, game_start 8 --hz 60: all IDENTICAL (same counts as the PP-layout runs); busy1 16 60 --neg: T-FRAME DIFFER (8,028 B/turn)
p2abtest.py --only pop2_spr pop2_spr16 pop2_ptr_a pop2_ptr_b pop2_clamp: busy1 @8 IDENTICAL (-6.40 % work/pass), game_start @8 IDENTICAL (-2.42 %), busy1 @16 IDENTICAL (-4.99 %), game_start @16 IDENTICAL (-0.36 %); --neg: BACK/WORLD/SHOWN DIFFER, MISMATCH
p2abtest.py --only pop2_tooltip --no-walk: busy1 + game_start @8 and @16 MHz: IDENTICAL (back 128, world 128, shown 127/128 turns)
```
Tooltip caveat: with `--no-walk` the pointer never rests on an icon, so the gate proves "no pixel changes outside a hover" on the relocated blob; its negative control (`--poke 12740:4e714e714e71`, `--neg`) did NOT differ,
i.e. it is not sensitive. Positive evidence that the relocated blob draws: the cold-boot hover shots (`work/shots/ics_ste512_cat2.png`: "EARTH EFFECTS / KEY: F3" on a 512 KB STE).

### Pattern fill with our patches active (`work/scratch/ics/memmap2.py`; menu, play, busy, effects, save+load, restart, conquest2, custom game as in section 2)
```
[mp512] 512 KB STE: free tail $7ec70-$7fff8: 0 longs changed at every step; lowram payload $7b400+14448: 0 non-zero image bytes differ at every step; RESULT ALL INTACT (custom game last)
[mp1m]  1 MB STE: $7b380-$7fff8 and $90000-$f8000: 0 longs changed; full payload $80000+32768: 0 non-zero image bytes differ; busy turn 5970, save+load 6641 -> 6654; RESULT ALL INTACT
```
So with every patch active nothing writes outside its own image (the data blocks inside the image are expected to change and are not compared).

### Three saves and a full disk (`saves3.py`, STE 1 MB, game disk, saves A1-A3 by typing the name in the game's requester)
```
A1 turn 90 / A2 turn 224 / A3 turn 362 saved, game back in play each time
A4: the game shows DISK FILE ERROR (work/scratch/disks/shots/sv3_a4_after.png); after OK + CANCEL the game is in play
GAM files: A1 A2 A3 GAM 56690 each; 5 120 bytes free (= the 5 spare clusters, nothing leaked by the failed 4th)
fsck.fat -n: 37 files, 706/711 clusters   (no error)
```
LOAD of A3 after that: game in play, turn 430 (saved at 362+; not conclusive by itself because the play ran 12 s after the click); load restoring the saved state is proven in the cells of section 6 (e.g. 619 -> 739 -> 632).
(First attempt: the FILE field kept the previous name and appended the new one: a test-script bug, fixed with BackSpaces.)

### STE 512 KB cold boot on the FINAL build (`c_ste512.log`)
```
CELL ste512: ... 512 KB (lowram layout); boot 114s in_play=True marker='P2PO' $22f14=4ef90007c780 ... payload $7b400+14448: 4100 non-zero image bytes, 0 differ in RAM
RESULT ste512 default MHz 50 Hz: 1501 VBL = 30.02 s, 160157 cycles/VBL, world turns 187 = 6.229/s
SAVELOAD {'turn_at_req': 619, 'turn_before_load': 739, 'turn_after_load': 632, 'load_play': True}; fsck.fat -n: 35 files, 594/711 clusters; LOG: 0 bus/address-error lines
```

### TT at 32 MHz: does the STOCK ICS crack fail too? YES
`work/scratch/ics/ttstock.py`: the UNMODIFIED ICS floppy (cracktro runs normally, space held), TT TOS 3.06 `--mmu true`, default 32 MHz, shifter sync forced to 50 Hz by a debugger write at `pc = $140` only so the game's
PAL check passes (the stock game otherwise stops at "SORRY PAL MACHINES ONLY" on a 60 Hz TT):
```
ttst32 cpuclock default game vbl installed True sync 0x2 turn 0     -> screenshot ttst32_stock_tt.png: "INSERT POPULOUS-II DISK / OK"
```
Same screen as our build, so it is the crack/game's own FDC routine on a fast CPU, not our patches. FLOPPY_LOWRAM.TXT says: TT at 8 MHz.

## 9. Reproduce
```
python3 tools/pop2patch.py verify --base ics
python3 tools/pop2patch.py build --base ics                    # build/ics/Populous2_lowram.st
python3 tools/pop2patch.py live --base ics --layout lowram --out build/live/ics_low   # (gates; json carries every patch's PB/DB)
python3 work/scratch/ics/cell.py --mem 512 --tag ste512 --saveload      [--machine st --tos 1.04 | megaste --tos 2.06 | falcon --tos 4.04 | tt --tos 3.06]
python3 work/scratch/ics/memmap.py <stock ICS .st> mm512 512
tools/package.sh lowram                                        # dist/Populous2_v<VER>_patched_floppy_lowram_<date>.zip (+ README.TXT from patches/FLOPPY_LOWRAM.TXT)
```
