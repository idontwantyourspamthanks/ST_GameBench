# Mega STE bank-tail corruption (v1.6 / v1.6.1 HD build): cause, impact, fix

Question (work/notes/stesound.md 7b): on a Mega STE (TOS 2.06, 1 MB) booted from the HD zip the last 13 714-13 716 bytes of the Amiga sound bank in RAM
(`$e2b6a`-`$e61b2`, the tail of the effect samples) differ from `build/asn_bank.bin`; on the STE (TOS 1.62) 0 bytes differ.
Tags: [obs] observed in a run (raw output `work/banktail/out/<cell>.txt`), [src] read in the HAGA disassembly, [INFERENCE] reasoning only.
Everything was run on the UNZIPPED SHIPPED v1.6.1 zips (`dist/Midwinter2_v1.6.1_patched_2026-11-20.zip`, RUNME.TOS md5 `470cfd0e574c7ac914312d400d170614`,
`FILES/ASNBANK.BIN` = `build/asn_bank.bin` md5 `c526427d8a1d93f2da60cd4102acdcb7`; the floppies zip), sound on (`--sound 50066`), private HOME, own workdirs `/tmp/mw2tail/<cell>`.
No tracked file was edited; the prototype fix lives in `/tmp/mw2tail/proto` (a copy of tools/ + patches/), its diff is `work/banktail/proposed_canary.diff`.

## 1. Result

* **Cause:** PP's HAGA (the original game's resident loader, file `HAGA`, loaded to `$F8000` = phystop-`$8000` on a 1 MB machine) keeps a **TOS<->game low-memory swap buffer** just
  below itself. Its init (`HAGA+$3122`, called once by RUNME *after* our bank load) copies the TOS low memory `[$8, A4)` there, with `A4 = RUNME text base + $9A4`, and the buffer starts at
  **`phystop - $8100 - A4`**. STE (TOS 1.62): `$E83E6`. Mega STE (TOS 2.06, whose TPA starts 22 652 B higher): **`$E2B6A`**, 13 896 bytes inside the end of our bank (`$BB000-$E61B2`).
  The bank is correct right after the load and is overwritten once, at HAGA's init (VBL 2331-2334, before the logo).
* **Not** TOS 2.06 as such, not HDDRIVER (Hatari's GEMDOS drive, no driver), not the game, not our patches, not a short read: it is the size of the TOS image HAGA saves. Any 1 MB machine whose
  RUNME text base is above **`$113AA`** loses the tail: plain STE TOS 1.62 `$F176` (8 756 B of headroom), Mega STE TOS 2.06 `$149F2` (13 896 B over). A resident stand-in of 16 KB in front of
  RUNME on the STE reproduces it (7 774 B differ). [INFERENCE: real 1 MB STEs with HDDRIVER, accessories or RAM disks are in the same class.]
* **Audible:** the damaged bytes are the last two effect sample regions = the **engine loops** of sound ids 17, 18, 19, 24, 25, 29, 30, 33, 35 (and the never-triggered 13). WAV of ids 17/19/24 on the
  Mega STE: 43 % / 23 % / 21 % of the energy above 1.5 kHz (STE: 20 % / 5 % / 2 %), spectral centroid 2x; the control effect (id 2) is identical. Music and all other effects are intact.
* **Floppy build: not affected** (no HAGA): bank == file at every checkpoint on Mega STE 1 MB and STE 1 MB. HD zip on 2 MB / 4 MB (STE and Mega STE): bank == file.
* **Fix:** minimal and safe = a 4-byte end canary (`ASNE`) checked by `asn_init0`: a machine whose bank tail was overwritten falls back to the YM driver instead of playing garbage (prototype built
  and run: Mega STE 1 MB -> YM, DMA off; STE and Mega STE 4 MB unchanged). Keeping the Amiga sound on a 1 MB Mega STE needs >= 13 896 B (7.9 %) less bank: an audio-content decision (section 7.2).

## 2. Is the tail wrong right after the load, or overwritten later? (question 1)

Breakpoints at the HAGA copy loop (`pc = $fb1f0` entry, `$fb204` exit; the same HAGA code at the same addresses on both machines) dump the bank around the overwrite (`savebin $bb000 $2b1b2`,
compared with `build/asn_bank.bin` outside state/records/ring `$BBE00-$BC7FF`; `walk.py`). Numbers = bytes that differ:

| cell (HD zip, sound on, cold boot) | HAGA entry (= after the load) | HAGA exit | logo | +20 s | M/J/K | hall | map | boss | 3D view |
|---|---|---|---|---|---|---|---|---|---|
| Mega STE TOS 2.06 1 MB, `hatari-option --cpuclock 8` (`ms8`) | **0** | 13 714 | 13 714 | 13 714 | 13 714 | 13 714 | 13 714 | 13 714 | 13 714 |
| Mega STE 1 MB, `--cpuclock 16` (`ms16`) | **0** | 13 715 | 13 714 | 13 715 | 13 715 | 13 715 | 13 715 | 13 715 | 13 715 |
| Mega STE 4 MB (`ms4`) | (HAGA at `$3f8000`) | - | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| STE TOS 1.62 1 MB (`ste1`) | **0** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| STE 1 MB + 4 KB resident stand-in (`wrap1100`) | 0 | 0 | 0 | | | | | | |
| STE 1 MB + 8 KB resident stand-in (`wrap2100`) | 0 | 0 | 0 | 0 | | | | | |
| STE 1 MB + 16 KB resident stand-in (`wrap4100`) | 0 | **7 774** (first `$e42d8`) | 7 774 | 7 774 | | | | | |
| floppy zip, Mega STE 1 MB (`fl_ms`) | - | - | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| floppy zip, STE 1 MB (`fl_ste`) | - | - | 0 | 0 | 0 | 0 | 0 | 0 | (3D step did not start in this script run, `$6220 = 0`) |

* Damaged runs: always `first $e2b6a last $e61b1` (13 896 bytes; 13 714-13 716 differ: about 180 bytes of the copied TOS memory equal the sample byte by chance and a few bytes are the live stack, so the
  count moves by +-2 between runs and with the clock). 8 vs 16 MHz makes no difference. The count is constant from the overwrite to the 3D view: the overwrite happens **once**, at HAGA's init;
  at HAGA's entry the whole bank, tail included, equals the file, so it is **not** a short read and **not** a later writer.
* Both Mega STE runs show `16MHz(CE)` in Hatari's status bar although `hatari-option --cpuclock 8` was sent in `ms8` (and `$ff8e21` reads `ff`: this build has no handler); the 8/16 labels are the project's
  convention. The bank result does not depend on it.
* Floppy: the HAGA breakpoints never fire and HAGA's record (`$f8094`) is zero: there is no HAGA on the floppy build ([src] work/notes/floppy.md l.24: RUNME/HAGA are not involved).
* Other RAM sizes (`haga_loc.py`, `out/haga_loc.txt`; boot to the logo, dump all RAM, find `HAGA rulez!`): HAGA at phystop-`$8000` everywhere (`$f8000`, `$1f8000`, `$3f8000`); its record at `HAGA+$94`:
  STE 1 MB swap start `$e83e6` (count 1339), Mega STE 1 MB `$e2b6a` (count 1811, bank 13 716 differ), Mega STE 2 MB `$1e2b6a`, Mega STE 4 MB `$3e2b6a` (same 86 976 B, at the top of RAM: bank 0 differ);
  STE 2 MB and STE 4 MB: bank 0 differ. Only the 1 MB size can collide, because the free window `$BB000...` is fixed while the buffer hangs from the top of RAM.

## 3. Who writes there (question 2)

1. First change of `$e2b6a` (`watch2.py`: `b ($e2b6a).b ! ($e2b6a).b :trace :once :file ...`): **`pc = $fb1fc`**, the loop `$fb1f4 movem.l (a5)+,d1-d7/a0-a4 / $fb1f8 movem.l d1-d7/a0-a4,(a6) / $fb1fc lea $30(a6),a6 /
   $fb200 dbra d0,$fb1f4`; at that hit `A5 = $38` (source, started at `$8`), `A6 = $e2b6a`, `D0.w = 1811`, supervisor mode, exactly 48 bytes changed. At the exit `A6 = $f7f2a`, `A5 = $153c8`:
   1812 iterations x 48 B = `$153c0` bytes, a plain copy of RAM `$8-$153c8` (146 of those bytes changed between entry and exit: the running stack).
2. `$fb1f4` is code of the `HAGA` file RUNME loads to `$f8000` (bytes `4cdd1ffe 48d61ffe 4dee0030 51c8fff2` at HAGA file offset `$31f4`, string `HAGA rulez!` at `$30f8`). [src] disassembly of the
   function `HAGA+$3122` (entry 13, "called once by RUNME": work/notes/loading.md, patches/pp_bigram_cache.s):
   ```
   a5 = $8 (source); a4 = end of the TOS image, passed in by RUNME
   d0 = (RAM size code at HAGA+$87) << 3 << 16        ; $100000 on 1 MB (code 2)
   a6 = d0 - a4 - $8100                                ; swap buffer start    (STE: $100000-$fb1a-$8100 = $e83e6)
   record at HAGA+$94 = {a6.l, (a4 div $30).w, ...}    ; $f8094 on 1 MB
   loop: (a4 div $30 + 1) x  movem.l (a5)+,d1-d7/a0-a4 ; movem.l d1-d7/a0-a4,(a6) ; a6 += $30
   ```
3. `A4` is **RUNME's text base + $9A4** (dumps at the HAGA entry: RUNME text at `$149f2` on the Mega STE and `$f176` on the STE, `A4 = $15396` / `$fb1a`). RUNME is what TOS loaded at the first free address above
   the OS, so the saved image is everything below the program: TOS (22 KB more on 2.06) plus whatever is resident. Formula `A6 = $f7f00 - A4` against the measured first `A6`:

   | cell | RUNME text base | A4 (obs) | swap buffer start (obs = formula) | overlap with the bank end `$e61b2` |
   |---|---|---|---|---|
   | STE TOS 1.62 | `$f176` | `$fb1a` | `$e83e6` | none, 8 756 B headroom |
   | STE + 4 KB (`wrap1100`) | | `$10c28` | `$e72d8` | none |
   | STE + 8 KB (`wrap2100`) | | `$11c28` | `$e62d8` | none, 294 B left |
   | STE + 16 KB (`wrap4100`) | | `$13c28` | `$e42d8` | 7 898 B (7 774 differ) |
   | Mega STE TOS 2.06 | `$149f2` | `$15396` | `$e2b6a` | 13 896 B (13 714-13 716 differ) |

   **The bank survives iff `A4 <= $11d4e`, i.e. RUNME text base <= `$113aa`.** (The stand-in `mkwrap.py` is a tiny RUNME.TOS that Mshrink()s itself to KEEP bytes and Pexec()s the real RUNME: the real RUNME and
   its `A4` sit KEEP bytes higher, as behind a resident program. An AUTO-folder TSR does not run under Hatari's GEMDOS-drive boot: `ste_tsr.txt`, `A4 = $fb1e`, no shift.)
4. The buffer is **live**, not a one-off backup (`swapwatch.py`, `out/swapwatch.txt`): at the first service call (VBL 2346) `$e2b6a` holds TOS's vectors (`02e010e2 03e010e2 ...`) and `$8` the game's
   (`0004deca ...`); at the end of the routine (VBL 2353) the two are exchanged. The exchange loop `$f93e4` ran 19 932 iterations = 11 services of 1 812 during the walk to the hall. HAGA swaps the whole TOS image
   in for every file service and back. Consequence for any fix: **nothing may write the buffer after HAGA's init** (loading the bank after the init would hand TOS a corrupt image at the next file load).
5. Not responsible: **our patches** (the bank equals the file at HAGA's entry; our HAGA edits are `$ffe-$fff`, `$1460-$14a5`, `$16da-$16db` (pp_nofade) and `$3228-$3229` (pp_bigram_cache, after the loop): 46 bytes differ from the original
   `HAGA`, none in `$31f0-$3200`); **TOS 2.06** and **HDDRIVER** (no driver runs; 2.06 matters only through its larger TPA start); **the bank loader** (reads the whole 176 562 B file).
6. The same HAGA code exists in the original game; it never showed because nothing lives in `$BB000-$E83E5`. The project's "free RAM" statement (`amiga_music_port.md` 1.1, `asn_build.py` `LIMIT = $E8000`,
   patches/README "RAM taken") was measured on TOS 1.62 only: it is the STE's window `$BB000` to `phystop-$8100-A4`, not a rule.

## 4. Audible impact (question 3)

* Damaged sample regions (`effects_in_tail.py`): `$e25d2-$e3bd2` (5 632 B, the first 1 432 B below `$e2b6a` are intact) and `$e3c02-$e6182` (9 600 B), both loops, used by sound ids **13, 17, 18, 19, 24, 25, 29, 30,
  33, 35**. Id 13 has no ST trigger; the others are the **engine loops** of nine of the 22 slots of the ST engine table (`$732c+2+4*type`: ids 29,32,20,30,31,8,18,33,27,26,19,23,34,21,35,36,25,37,22,28,24,17;
  slots 0, 3, 6, 7, 10, 14, 16, 20, 21 = ids 29, 30, 18, 33, 19, 35, 25, 24, 17; id 17 is also the fixed `$66` request; slot-to-vehicle names not mapped). The helicopter engine (id 21), the weapon launches
  (ids 1-4, 10, 12, 39, 40) and all tunes are in intact data. The voice dump confirms the damaged data is what plays: effect 17 -> voices on `$d202a` and **`$e3c02`**, 19 -> **`$e25d2`** + **`$e3c02`**, 24 -> **`$e25d2`** (`out/ms8.txt`).
* What the bytes are: 90 % of the 13 896 bytes are zero (TOS's low memory), the rest vectors/pointers (byte rms 16.5 vs 35.0 expected, rms of the difference 38): a looped engine becomes mostly silence plus a crackle.
* Recorded (Hatari WAV 50066 Hz at the 3D view, the helicopter engine request switched off with `w $18eec rts`, effects requested like the game does through `$6862 = id*6`, 10 s apart, `walk.py --fx`, `fxwin.py`;
  windows = request to next request, loops keep playing so later windows contain earlier voices; the WAVs are Amiga sample material and are not kept in the repo, `/tmp/mw2tail/keep`):

  | cell | id 2 (control, intact data): rms / centroid / energy > 1.5 kHz | id 17 | id 19 | id 24 |
  |---|---|---|---|---|
  | STE 1 MB (`ste1`) | 2341 / 526 Hz / 1.8 % | 949 / 1530 Hz / 20.2 % | 1344 / 651 / 4.9 % | 1172 / 445 / 1.7 % |
  | **Mega STE 1 MB 8 MHz (`ms8`)** | 2340 / 526 / 1.8 % | **682 / 2555 / 43.4 %** | **950 / 1388 / 22.6 %** | **917 / 1307 / 20.9 %** |
  | **Mega STE 1 MB 16 MHz (`ms16`)** | 2341 / 526 / 1.8 % | **703 / 2561 / 43.5 %** | **951 / 1389 / 22.6 %** | **915 / 1306 / 20.9 %** |
  | Mega STE 4 MB (`ms4`, intact; request order 17,19,24,2) | | 939 / 1526 / 20.0 % | 1357 / 644 / 4.8 % | 1173 / 445 / 1.7 % |
  | floppy Mega STE 1 MB (`fl_ms`, intact; same order) | | 934 / 1543 / 20.3 % | 1352 / 644 / 4.8 % | 1174 / 445 / 1.7 % |

  The intact machines agree within 2 %; the damaged Mega STE runs differ by 2x in centroid and 4-12x in high-band energy on exactly the three damaged ids, the control is identical to 4 digits.
  (Waveform cross-correlation does not work here: two intact runs only correlate 0.5-0.8, the request lands at another VBL phase.)
* Not checked: how it sounds to a person on hardware [INFERENCE: thin, crackling engines on nine vehicle slots]; which missions spawn those vehicles.
* Music is not touched: the tunes sit at `$C1000-$D2029`, it would take a buffer start below that (a resident size of about 155 KB); the DMA tune played from the logo to the map on every Mega STE run
  (`SV mode 2`, `$5138 = $bf81e`).

## 5. Affected builds and machines (question 4)

| build / machine | affected |
|---|---|
| HD zip v1.6 and v1.6.1, Mega STE TOS 2.06, **1 MB** | **yes** (13 714-13 716 B, effect tail; 8 and 16 MHz). v1.6: same tail plus the old blob (stesound.md 7b) |
| HD zip, STE TOS 1.62 1 MB, nothing resident | no (8 756 B headroom) |
| HD zip, any 1 MB machine with RUNME text base > `$113aa` (a plain STE with > 8.7 KB of resident code; an STE with TOS 2.06) | yes [obs for the stand-in; real driver sizes [INFERENCE]] |
| HD zip, 2 MB and 4 MB, STE and Mega STE | no [obs] |
| HD zip, TT TOS 3.06 4 MB | no (stesound.md 7b: 0 differ; YM machine) |
| floppy zip, Mega STE 1 MB and STE 1 MB | no [obs] (no HAGA) |
| ST / Mega ST (no DMA) | n/a (YM; the bank is never used) |

## 6. Why no gate caught it

The bank check ("bank in RAM = file outside state/ring") ran on the STE only; on the Mega STE the tail difference was seen in 7b but recorded as an observation, the line is not an assertion. The matrix that
catches it: STE 1 MB TOS 1.62 and Mega STE 1 MB TOS 2.06 (8 MHz), HD zip, bank check at every checkpoint, plus the stand-in `mkwrap.py 2100` (pass) and `4100` (fail without a guard):
`run_all.sh`, `run_wrap.sh` are those cells.

## 7. Proposed fix (question 5)

### 7.1 Minimal and safe now: end canary + init gate (prototype built and run)

* `tools/asn_build.py` `build_bank`: after `b += smp` append `b"ASNE"` (end canary; `total` includes it, so `BANK+12` = the header's total length): bank 176 562 -> 176 566 B.
* `patches/asn/blob.s` `asn_init0` (the once-only machine gate), after the `cmpi.l #BANK,BANK+8.l` test:
  ```
          lea     BANK-4.l,a0
          adda.l  BANK+12.l,a0            ; end of the bank
          cmpi.l  #'ASNE',(a0)
          bne     .rts                    ; overwritten (HAGA's swap buffer): stay in mode 1 = the YM driver plays, the DMA is never touched
  ```
  and `beq.s asn_run` -> `beq asn_run` at `.m:` (the 12 added bytes push `asn_run` out of byte-branch range; blob 3 624 -> 3 646 B, zone `$4800-$6000`). Diff: `work/banktail/proposed_canary.diff`.
  The overwrite always covers the END of the bank (the swap buffer is contiguous up to `$f7f2a`), so an end canary detects every HAGA case and any other writer of the tail.
* Files that change: `tools/asn_build.py`, `patches/asn/blob.s`; then rebuilt `build/asn_bank.bin`, RUNME.TOS (the splice embeds the bank length; prototype md5 differs), `FILES\ASNBANK.BIN`, the floppy FFA payload
  (+4 B; the prototype floppy build runs through, 46 track-sides unchanged [INFERENCE: not run in Hatari]); docs: `patches/README.md` (Machines / RAM taken: the window is `$BB000` to `phystop-$8100-A4`, not `$E83E5`;
  Gates), `asn_build.py` docstring + `LIMIT` comment, `work/notes/stesound.md` 7b, a line in the release notes.
* **Prototype results** (HD build of `/tmp/mw2tail/proto`, cells `pr_*`, `out/pr_*.txt`; all at logo, +20 s, M/J/K, hall):

  | cell | bank vs its file | SV mode / act / dma | `$ff8901` | sound |
  |---|---|---|---|---|
  | Mega STE 1 MB TOS 2.06 (`pr_ms`, `pr_ms_w`) | 13 720 differ (tail), canary `00000000` | **1** / 0 / 0 (YM) | `00` (DMA off) | YM tune audible, rms 3517-3906 per second over 15 s |
  | STE 1 MB (`pr_ste`, `pr_ste_w`) | 0 differ, canary `ASNE` | **2** | `03`, `$ff8921 = 81` | DMA tune, rms 2230-2950 |
  | Mega STE 4 MB (`pr_ms4`) | 0 differ, canary `ASNE` | **2** | | |

  The garbage engines become the shipped YM behaviour on the damaged machines; every other machine is unchanged. Cost: one `cmpi` at the first tick. Not run with the prototype: the 3D view, 16 MHz, floppy in Hatari.
* Gate (for `asn_mus_cold.py` / `asn_cold.py`): at every checkpoint **either** (bank == file AND mode 2 AND canary `ASNE`) **or** (canary bad AND mode 1 AND `$ff8901 == 0` AND YM audible).
  Expected: STE 1 MB first; Mega STE 1 MB TOS 2.06 second; Mega STE 4 MB first; `mkwrap.py 2100` first; `mkwrap.py 4100` second; floppy Mega STE first. Negative control: the shipped v1.6.1 bank fails on the Mega STE 1 MB
  (mode 2 with a bad canary).

### 7.2 Keeping the DMA sound on a 1 MB Mega STE (bank == file at every checkpoint): a smaller RAM footprint

Budget: the bank must end at or below `phystop - $8100 - A4`: **`$E2B6A` on the Mega STE (TOS 2.06) = at most 162 666 B (-13 896 B, -7.9 %)**; each resident byte lowers it 1:1 (STE: 185 318 B, 8 756 B to spare).
No lossless saving of that size exists: the zero/slack areas inside the bank total about 6 KB (ring 2 048 B + state 256 + channel records 256 + `$40-$FF` 192 + blob slack 2 490 + 16 sample pads 768).
Content: effects 82 312 B (16 regions), instruments 55 464 B (tune 1 alone owns 22 668 B: the logo/hall/map tune; dropping any other single tune frees 0.3-1.9 KB), VTAB 12 288 B, score 14 210 B. Options:
  1. drop, or alias to an intact loop, the two damaged engine regions = **15 296 B** (nine engines get another vehicle's loop): the bank ends `$E25D2`; margin on the Mega STE only 1 432 B.
  2. as 1, plus the engine-only regions `$e12a2`/`$e0f72` (id 26, 5 680 B) and `$e01c2` (id 18, 3 504 B): margin about 10 KB (a Mega STE with 10 KB of resident code, an STE with about 19 KB).
  3. keep the audio and load the damaged tail above HAGA: `$FB614-$FFFFF` (18 924 B) was constant (12 non-zero bytes) at logo/M/J/K/hall/map/boss/3D on STE and Mega STE 1 MB. Costs: a second `Fread` in the RUNME
     splice, an address-bound second block (every region address is baked into the records at build time, so the 2/4 MB machines, where `$FB614` is ordinary RAM, need a walk of their own), the floppy payload copy;
     War Room / Raids / mission end were never walked. [INFERENCE] Not minimal.
  Gate for any of them: bank == file at every checkpoint on STE 1 MB, Mega STE 1 MB (8 and 16 MHz), Mega STE 4 MB, `mkwrap.py 2100`; the 7.1 canary stays as the safety net (`mkwrap.py 4100`).
  Recommendation: ship 7.1 (a correctness fix, no audio loss for anyone not damaged today) and decide 7.2 by listening; option 1 is the smallest audio change.

## 8. Which sounds break as a 1 MB machine gets more resident code

Region k (end address E_k) is damaged iff `phystop - $8100 - A4 < E_k`. From the top: `$e6182` (ids 13, 17, 18, 19), `$e3bd2` (19, 24, 25, 29, 30, 33, 35), `$e25a2`/`$e1272` (26), `$e0f42` (18), ..., until the music
at `A4 > $25ed7` (`$d2029`); the exact id list per region is `effects_in_tail.py`.

## 9. Files (all new and untracked; no tracked file edited)

`work/notes/banktail.md` (this note); `work/banktail/`: `bt.py` (helpers; `BT_BANK` = bank file to compare with), `walk.py` (cold-boot walk with the bank check at every checkpoint, HAGA breakpoints, `--fx`, `--wav`, `--auto`, `--wrap`),
`watch1.py`, `watch2.py`, `watch3.py` (first-write watch, HAGA loop breakpoints), `swapwatch.py`, `haga_loc.py`, `effects_in_tail.py`, `fxcmp.py`, `fxwin.py`, `mktsr.py` (AUTO TSR: does not run in Hatari's GEMDOS boot, kept for the record),
`mkwrap.py` (the working resident stand-in), `run_all.sh` (cells ste1|ms8|ms16|ms4|ste_tsr|fl_ms|fl_ste), `run_proto.sh`, `run_proto2.sh`, `run_loc.sh`, `run_loc2.sh`, `run_wrap.sh`, `proposed_canary.diff`,
`out/` (raw results: `<cell>.txt/.json`, 3D screenshots, `swapwatch.txt`, `haga_loc.txt`). Reproduce: unzip the two release zips to `/tmp/mw2tail/rel/{hd,fl}` and run the scripts from the project root.

## 10. Caveats

* The 3D view of the prototype build, the prototype at 16 MHz and on the floppy in Hatari were not run; the 3D view with effects on the damaged shipped build was (`ms8`, `ms16`). `fl_ste`'s 3D step did not start (script, not the bank).
* Real hardware and real driver sizes were not measured (`mkwrap.py` is a stand-in). `$ff8e21` / the Mega STE clock were not verified beyond `hatari-option --cpuclock`.
* While chaining runs a second chain started by mistake ran a duplicate `ms16`/`ms4` cell next to `ms8` for a few minutes (two Hatari instances at once); the duplicate `ms16` was killed and its output discarded, the numbers above are
  from the clean re-runs. One `kill` also hit the parent process of that chain (an `omp` helper); nothing else of mine or anyone's was touched as far as I can see.
