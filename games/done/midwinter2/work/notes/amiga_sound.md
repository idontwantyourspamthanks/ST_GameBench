# Midwinter 2: the Amiga sound effects on the STE's DMA sound (patch group `asn_*`)

Evidence tags: **[obs]** observed in Hatari / a tool run in this session; **[disasm]** read from disassembly (ST: `work/dumps/ram_ingame_lobos.bin`,
address = file offset, `tools/m68dis.py`; Amiga: `Amiga/.../Midwinter-2/work/dumps/mwii_flat.bin`, see §2.0 for its addressing); **[model]** computed by the
Python model / Unicorn tests of this group; **[INFERENCE]** not verified.
Nothing from the Amiga disks is in git: the ADFs are copied to `alt/amiga/` (git-ignored, `.gitignore:61 games/*/*/alt/`), the sample bank is built into
`build/asn_bank.bin` (git-ignored, `**/build/`), WAV captures go to `work/snd/` and `work/asn_cold/` (`.gitignore:75 **/work/snd/`; `work/asn_cold/*.wav` (covered by `.gitignore:73 **/*.wav`)).

> **Superseded layout (music port).** The numbers in this note for the bank layout are those of the sound-effects-only bank and are OUT OF DATE: the blob is now at `$BF800` (7 fixed `jmp abs.l`
> entries), not `$D5600`; the ring is 2048 B (was 1024); the effect sample pads are 48 B (were 800); the bank is 176 562 B and ends at `$E61B2` (was 110 KB / `$D5E9E`); its header is `ASN2`.
> The sound-effect logic and the evidence here still hold. Current numbers: `work/notes/amiga_music_port.md` section 1.2, the docstring of `tools/asn_build.py`, `patches/README.md`.

## 0. Verdict (details and numbers below)
**Feasible, built, and works in Hatari on STE / Mega STE (1 MB HD and floppy build).** The ST game already contains a near copy of the Amiga's sound driver
(same sound ids, same sequence/record tables layout, same request words); the Amiga data (41 sound rows, 818 B of sequences, 58 effect records, 16 looped
samples = 81544 B) is in the load file `MWII`. The new blob is a port of the Amiga driver (4 voices) feeding a software mixer that streams a 1024-byte ring
through the STE DMA at 6258 Hz mono. Cost (8 MHz STE, 160256 cycles per VBL): 1 voice 8.1 k cycles (5.0 %), 3 voices 13.4 k (8.4 %), nothing playing 1.3 k (0.84 %) against the original YM tick's 1.2 k (0.73 %).
RAM: the bank is 110 KB of the free `$BB000-$D5E9E` (1 MB build; free RAM runs to `$E83E5`), so it does not need 2 MB. The HD delivery is the hard part (PP's loader caps RUNME's size on 1 MB
machines, §3.2): the bank is a separate file `FILES\ASNBANK.BIN` read by a 94-byte splice in RUNME; the floppy payload moves to FFA's blank track-sides 81-112.

## 1. ST side

### 1.1 Is it the Hunter / Rainbird driver? No. It is a port of the AMIGA driver.
- **Tick and rate.** The VBL handler `$26298` ends with `0262ec: bsr.w $26342 / 0262f0: movea.l $5138.w,a0 / 0262f4: jsr (a0) / 0262fa: rte` [disasm]. `$5138` = `$513c` =
  `$18f92` in the in-game dump (`005138: 00018f92`, `00513c: 00018f92`) and the sound init `018e32: move.l #$18f92,$513c.w` (reached through the jump table
  `$5122`, caller `$27ed4`) [disasm]. Outside the 3D view `$5138` is `$0d0e` (the YM music driver's update, floppy cold boot with `asn_cold.py --watch`: `$5138 = 00000d0e` until the game installs its sound tick, then `00018f92`). So the sound driver runs once per VBL (50/60 Hz), no timer. It lives in the overlay `FFB f1` (`$18d96-$210b2`).
  `$18f92`: `move.w $6862.w,d0 / bmi.b $18fa2 / move.w #-1,$6862.w / bsr $18efc` = take the request, `$18fa2..$18fdc` run 3 voices (`$18fe2` x3) then
  `bsr $19182`, the only PSG writer of the 3D view (`019184: lea $ff8800.l,a0` then `movep.w d0,0(a0)` x11) [disasm].
- **Structure = the Amiga driver minus samples.** ST: request word `$6862` (-1 = none), `$686c` = the sustained sound that is re-requested when all voices
  are idle (`018fb4: move.w $686c.w,d0 / bmi / bsr $18efc`), `$19218` = engine level, sound rows (3 words per id, 6 bytes) at `$19e32`, sequences `$199a8`,
  effect records `$1921a`, 3 voice records of `$10` bytes at `$682c`, group bytes `$6869..` (`018f24: lea $6869.w,a2`). Amiga: request `$56820`, last
  `$5732c`, level `$5676a`, rows (4 words, 8 bytes) at flat `$300e8`, sequences `$2fdb6`, records `$2f75c` (28 bytes), 4 voices of `$16` bytes at `$5676c`,
  group bytes `$56829..` [disasm, §2.1]. `$18efc` is `$2f28c` (start / kill; 3 channels of `$10` bytes instead of 4 of `$16`), `$18fe2`+`$190c2` are `$2f46c`+`$2f4fa` (voice update / next step, with the YM fields) [disasm side by side].
- **Sound id = request word / 6 on the ST, / 8 on the Amiga.** Immediates written to the request word, in code order: ST (`move.w #n,$6862.w`) `$18,$ea,$ea,$3c,
  $3c,$06,$f0,$0c,$12,$06` = ids 4,39,39,10,10,1,40,2,3,1 and the stub `$18e3c: move.w #$48,$6862.w` = id 12 (jump table `$5128`, callers `$326d8`, `$339f8`);
  Amiga (`move.w #n,$56820.l`) `$138,$20,$138,$138,$50,$50,$8,$140,$10,$18,$8` = ids 39,4,39,39,10,10,1,40,2,3,1 and `$2f1b6: move.w #$60,$56820.l` = id 12 [disasm].
  The Amiga has one more `39` at flat `$2068` (11 sites against 10); everything else is the same list in the same order. The engine sounds:
  `$18e44` (per frame, `jsr $5128`'s neighbour `$512e` from `$31564`) and Amiga `$2f1c0` (`move.w $5f3b0.l,d0 ... bsr $2f276`) load `d1` from a per-vehicle-type
  table (ST `$732c+2+4*type`: ids 29,32,20,30,31,8,18,33,27,26,19,23,34,21,35,36,25,37,22,28,24,17 [obs, RAM dump]; the Amiga table `$6078a` is filled at
  run time from the vehicle data and is zero in the load file, so the Amiga's own per-type ids were NOT read [INFERENCE: same vehicle data file, same ids]).
  Fixed ones: `$66`/`$60`/`$30` = ids 17 / 16 / 8 on the ST (`018e6a`, `018e82`, `018e98`), `$88`/`$80`/`$40` = ids 17/16/8 on the Amiga (`$2f1ec`, `$2f206`, `$2f21c`).
- **Who triggers what** (ST, from the `$6862` writes; the weapon routines `$1ad1e..$1b320` each end with `move.w #id,$6862.w` after `jsr $4f00`, which spawns the
  shot): id 4 `$1ad58`, id 39 `$1ae26/$1af22`, id 10 `$1b002/$1b05a`, id 1 `$1b0ee/$1b314`, id 40 `$1b146`, id 2 `$1b1e0`, id 3 `$1b27a` = the player's weapon
  launches; id 12 = `$326d8` / `$339f8` (a unit within `$400` of the player: `cmp.w #$400,d1 / bgt`); ids 8, 16, 17..37 = engines of the vehicle types (above), re-requested
  through `$686c` while the vehicle runs. Ids 0, 5-7, 9, 11, 13-15, 18, 38 have rows but no ST trigger [disasm: no other write of `$6862`; raw scan for the word `6862`
  in `$800-$3e000` finds only `$18e40,$18ef4,$18f94,$18f9c` and the weapon sites]. Names of the weapons were not resolved.
- **Channels.** 3 YM voices (A, B, C) on the ST, 4 Paula voices on the Amiga. Rows differ: Amiga row 8 `[--,01c,048,024]`, ST row 8 `[0dc,070,080]` (three voices each); the one-voice
  gun sounds use Amiga voice 0 and the ST noise voice [disasm of both tables]. The port does not use the ST rows at all.
- **Update rate / real time.** The tick is the VBL (50 or 60 Hz, `$ff820a` bit 1), not the 5 Hz world tick or the render frame, so the sound follows real time already.
  The game writes `$6862` from its logic (once per 5 Hz tick, and weapon fire) and `$19218` once per frame; the driver consumes them on the next VBL.
- **Music** is separate: the title/menu YM driver at `$c00-$1240` with its own vector table `$806..` (jump targets `$d0e`, `$c6c`, `$c4c`) [disasm]; the in-game tick above
  is not involved. In DMA mode the first tick of a session silences the YM once (as Hunter does), nothing else touches it.

## 2. Amiga side

### 2.0 Where the data is
- The three SPL disks are plain OFS (`xdftool`); **no sound or sample file exists**: `Disk 1 program` has `MWII` (505488 B, md5 `d7c1518e6702c3210a748fc40a1ed753`), `cods.bin`
  (38036 B, vehicle/object tables), `midword.fsd` (4704 B, a picture); disks 2/3 hold `grafix/*`, `missions/*` [obs: `xdftool ... list`, `unpack`]. Samples and tables are
  inside `MWII`: hunk 0 CODE (217912 B) carries the driver's tables as data; hunk 3 DATA (138204 B, chip) begins with the sample pool [obs: `tools/asn_build.py stats`].
- The flat dump `mwii_flat.bin` (Amiga repo) is `amigabin flat` with operands relocated against a base of `$270d0` per hunk-0 byte: the operand `$5676c` is flat offset
  `$2f69c`; hardware writes `addi.l #$89478,d0` = hunk 3 base (reloc target hunk 3, offset 0) [obs: reloc table of `MWII`].

### 2.1 The Amiga driver (all flat addresses; operand = flat + `$270d0`)
`$2f3b2` tick: consume `$56820` (`bsr $2f28c`), if every voice's counter (`$8,$1e,$34,$4a` of the voice records) is 0 re-request `$5732c`, run `$2f46c` for the 4 voices
(Paula channel masks 1,2,4,8), then `$2f616` writes AUDxPER and AUDxVOL (high byte of the 8.8 volume). `$2f28c` start: a row (4 words at `$571b8 + 8*id`) kills the group of every
channel it names (`$2f2f2`), allocates the first free group byte and primes counter 1 / sequence offset / group of each named channel. `$2f46c` voice: counter-1; 0 = next step
(`$2f4fa`: sequence word -> effect record offset, 0 = stop, negative = relative jump back; the record gives start volume, slope, acceleration, clamps, period or the engine
form `base + scale * level`, duration in ticks (0 = 7), sample address and length in words; the DMA is restarted at phase 0), else volume and period integrate
(`vol += slope`, `slope += accel`, clamped). The samples loop for the whole step. Details of the ported maths: `patches/asn_core.s`, `tools/asn_model.py`.
**Port check [model]:** the ORIGINAL Amiga routine `$2f3b2` from the load file runs in Unicorn (tools/asn_test.py `unit`), and after every tick its AUDxPER / AUDxVOL / AUDxLC /
AUDxLEN equal the blob's voice state for 41 sounds x 3 levels x 200 ticks incl. retriggers and sustained re-requests: 0 mismatches. Negative control (blob level +1): 57 mismatches.

### 2.2 Sound list (tools/asn_build.py stats; periods from the model driver, rate = PAL 3546895 / period)
41 rows (ids 0-40), 58 records, 16 distinct loop regions, pool 81544 B, signed 8-bit, DC offset about +10 (removed in the bank), peaks 55-127.
| id | voices | length | rate range | note |
|---|---|---|---|---|
| 1-4, 10, 12, 38-40 (weapon launches, id 12 "unit near") | 1 | 20-100 ticks | 4.0-14.3 kHz | one-shots built from the regions 50568 / 15624 |
| 5-7, 9, 11, 13-15 | 1 | 30-100 ticks or sustained | 3.6-13.6 kHz | no ST trigger |
| 8, 16, 17..37 | 1-3 | sustained loops | 3.1-11.8 kHz | vehicle engines; pitch = `base + scale * level` (level 2..9) |
Rates up to 14.3 kHz are above what 6258 Hz can carry (Nyquist 3.1 kHz), as with Hunter; the mixer steps the phase with zero-order hold (what Paula does) so the sounds are duller.
Amiga MUSIC: `MWII` has a second Paula routine (flat `$30500-$30b60`, 8 tracks, tune table `$57e78`) = a tracker-style player (probably the title/hall tunes [INFERENCE: which screens was not checked]), with instruments presumably in the rest of hunk 3
(about 56 KB of non-sfx audio-like data [INFERENCE from the sample statistics]); the only ProTracker module found (`M.K.` at `INTRO+$3834`) is the cracktro's, not the game's. Not used here (out of scope).

## 3. Budget (1 MB STE, 8 MHz)

### 3.1 RAM
- Free RAM of the in-game 1 MB layout is `$B2852-$E83E5` (skill mw2-patching / payload32k.md); the existing payload takes `$B3000-$BAFFF`. The bank takes `$BB000-$D5E9E`
  (110238 B: header+tables `$3400`, 16 sample regions with 800-byte loop pads 94344 B, zeros to `$D5600`, blob `$D5600-$D5E9E`), 74 KB of free RAM are left to `$E83E5`.
  So **1 MB is enough; 2 MB is not needed.** Integrity over a whole session [obs, asn_cold.py]: the bank and the blob in RAM equal `build/asn_bank.bin` byte for byte (outside the
  state `$BBE00-$BBEFF` and the ring `$BC000-$BC3FF`) after the M/J/K screen, hall, map and at the 3D view, on STE 1 MB HD, STE 1 MB floppy, Mega STE 4 MB HD, ST 1 MB HD, TT 4 MB HD.
- Sample sizes [model]: the 15 regions the ST can reach are 81344 B native (all 16: 81544 B); stored native because the pitch is applied by the mixer. Pre-resampled variants
  (one copy per region at the output rate, never below native) would be 91 KB at 6258 Hz, 145 KB at 12517 Hz, 285 KB at 25033 Hz: 12517 Hz would not fit comfortably in 1 MB
  and costs double the CPU, 6258 Hz (Hunter's pick) is used. Volume tables 2 x 16 x 256 B = 8 KB, loop pads 12.8 KB (800 B x 16: the mixer reads a block past the loop end without a
  bounds check), ring 1 KB.

### 3.2 Delivery: the real constraint of the HD build (not RAM)
- **The bank cannot ride in RUNME's data segment.** The first attempt (payload 32 KB -> 151 KB, `tools/mw2patch.py`'s mechanism) stops on every 1 MB machine with "Too much low RAM
  occupied. Read usage how to fix it." [obs: Hatari screenshot `work/asn_cold/hd_ste162_1mb_exc.png` / `--trace gemdos` log]. The check is in RUNME's startup, text `$b4-$e4`
  (file offsets `$d0-$100` in `m68dis`): `lea $4772(pc),a1 / adda.l #$8000,a1 / cmp.b #2,d4 / bne / cmpa.l #$38270,a1 / bcc error` with d4 = HAGA's RAM class (2 = 1 MB, 4 = 2 MB, else
  `$61a80` / `$14e790`) [disasm of `work/dumps/RUNME_unpacked.tos`]. i.e. RUNME's bss start + `$23c` + `$8000` must stay below `$38270` on a 1 MB machine. RUNME's TPA starts at `$F176`
  (TOS 1.62) / `$149F2` (TOS 2.06) [payload32k.md], today's bss starts at `$1B6CE` / `$20F5A`, so the data segment may grow by only ~84 KB (TOS 1.62) or ~61 KB (TOS 2.06) in total,
  and any AUTO program or accessory takes from that. The 32 KB payload already uses half of it. A bank of 110 KB is impossible there at any price.
- **Chosen HD delivery: a separate file `FILES\ASNBANK.BIN` read by a splice in RUNME** (tools/mw2patch.py (the bank delivery is now in the stock tool)): the 6 bytes `lea $9a0.l,a7` at RUNME text `$46` (right after RUNME's own
  `Fclose` of HAGA, before the stack switch and the takeover) become `jmp bankload.l`; the 94-byte `bankload` (appended to the data segment, its two absolute operands relocated) does
  `Fopen("FILES\ASNBANK.BIN")`, `Fread(110238, $BB000)`, `Fclose` with every register preserved, then the displaced `lea` and `jmp text+$4c`. A missing file is skipped (no bank = original
  sound). RUNME grows by 96 bytes (50678 -> 50774), its TPA end does not move. [obs: `--trace gemdos`: `Fopen("FILES\ASNBANK.BIN")`, `Fread(64, 110238, 0xbb000)`, `Fclose(64)`, then the normal HAGA path.]
  The harness copies `FILES/` whole, so the file travels with the images; a distribution needs the file next to `FILES\FFA..FFE`.
- **Floppy**: the bank follows the payload in FFA file 10 (payload + bank = 143006 B = 32 track-sides). The old window (track-sides 72-79) is too small, but FFA's track-sides 81-159 (side 1, tracks
  1-79) are blank ($F6, checked by `floppy_ffa`), so file 10 starts at track-side 81 (`PAYLOAD_TS`, `FFA_BLANK_END` 160). Cost: about 8 s more loading at boot [INFERENCE: 28 more track-sides at
  ~0.3 s]; the disk-copy functions ("Start New Campaign", back-ups) copy the whole disk, so nothing is lost.

### 3.3 CPU (Hatari 2.6.1, `profile cycles`, STE 8 MHz, 160256 cycles per VBL = 100 %; snapshot `raid_jeep_dhafra`, tools/asn_live.py `cost`)
| scenario | blob cycles per VBL | % of CPU | note |
|---|---:|---:|---|
| original game, YM tick (`$18f92..$19200`) | 1173 | 0.73 % | driver + register writes |
| patched, no sound playing | 1339 | 0.84 % | driver tick + prep; +166 over the YM tick |
| 1 voice (the jeep's own engine) | 8083 / 8064 / 8062 | 5.0 % | measured three times (snapshot, HD cold boot, floppy cold boot) |
| sustained id 17 (2-channel row) | 8903 | 5.6 % | second voice mostly below the audible threshold |
| sustained id 36 (3-channel row) | 13448 | 8.4 % | |
| id 36 + id 14 requested (4 channels in the table) | 14035 | 8.8 % | voice count at the time not polled |
| plain ST / TT (YM path, `jmp` + 2 tests) | 157 | 0.1 % | cold boots, `profile` |
(the table's `%` column is of 160256; the "total 141 k per VBL" the profiler reports is the game's own busy time.) Per voice and sample the mixer needs 40 cycles (first voice, store) or 48
(added voice): 125 samples per VBL = 5.0 k and 6.0 k cycles; a full 4-voice mix costs about 1.5 k + 5.0 k + 3 x 6.0 k = 24.5 k = **15 % worst case** [model, from the instruction timings].
fps over 500 VBL (frames last whole VBLs): original 4.0 (12.5 VBL/frame), 1 voice 3.9, id 17 3.8, id 36 3.6 [obs]; in the 1000-VBL abtest runs 3.1 -> 3.2 and 4.2 -> 4.0 (noise of ±0.2).
So the typical cost is 5-6 % of a frame while an engine runs (about 0.2 fps at 4 fps) and about 9-10 % with a 3-voice sound; nothing between sounds.

### 3.4 Timing: the 5 Hz tick and the 25 Hz passes
- The sound tick is the VBL, so it is independent of the render frame and of p3cp_head's passes: ids requested from the logic (weapon fire, `jsr $5128`) are written once per 5 Hz tick
  (fire: once per world step since `p3cp_keys`) and consumed on the next VBL; the 3 `$19218` writers run once per frame in `$18e44` (`$31564`, logic block; [INFERENCE: PH 1 only]), so engine pitch
  follows at the game rate exactly as the YM did. The driver tick is 50 Hz of real time at both refresh rates: at 60 Hz (shifter sync `$ff820a` bit 1 clear) five of six VBL run it
  [obs: with `w $ff820a $00`, sound 2 lasts 0.50 s and sound 4 0.90 s as at 50 Hz (tools/asn_live.py record hz60); that the emulated refresh really changed was not measured separately].
- The mixer tops the ring up every VBL to 192 samples (30.7 ms) ahead of the DMA position (read with `movep.l` of `$ff8909`), ring 1024 B = 164 ms. Request-to-sound latency: up to one VBL + 30.7 ms.
  If the VBL stops (disk loads with interrupts masked) the ring repeats its last 164 ms until the VBL returns; `asn_wd` then stops the DMA within 2 VBL if the tick is no longer called.

## 4. Verdict
**Feasible, and built.** Numbers: RAM 110 KB of the 184 KB free in a 1 MB build (not 2 MB), CPU +0.1 % idle, +5 % with one voice, +8-9 % with three, 15 % worst case; HD needs one extra file and a 94-byte
splice in RUNME because PP's loader caps RUNME's size on 1 MB machines; floppy needs 32 of FFA's 79 blank track-sides. Why it is easy here: the ST game already carries the Amiga driver's logic and ids, and the
Amiga data is a few KB of tables plus 81 KB of samples inside `MWII`. Why it is not free: the 5 fps game is CPU-bound, so each audible voice costs about 3.5 % of the machine.

## 5. What was built (all `default: no`)
| file | role |
|---|---|
| `patches/asn_core.s` | site `$18f92` (deferred, FFB f1 overlay): `move.w $6862.w,d0 / bmi.b $18fa2` -> `jmp $d5600.l` |
| `patches/asn_wd.s` | site `$262c2` (boot, VBL handler's `jsr $27228.l`) -> `jsr $d5e00.l`: the watchdog |
| `patches/asn_lvc.s`, `asn_lv1.s`, `asn_lv2.s` | sites `$18ed8` (clamp 1..7 -> 2..9), `$18e72`, `$18ea0` (`move.w #7,$19218` -> 9): the Amiga's engine level range, only while the DMA driver runs |
| `patches/asn/blob.s` | the code (not a patch: in a subdirectory the patch loader skips): tick, Amiga driver port, mixer, DMA, watchdog, level stubs; assembled into the bank file at `$D5600` |
| `tools/asn_build.py` | bank builder (`build`, `stats`, `wav DIR`): reads `alt/amiga/disk1.adf` (md5-checked `MWII`), writes `build/asn_bank.bin` |
| `tools/asn_model.py`, `asn_test.py` | Python model of the Amiga driver and mixer, Unicorn tests (`unit`) incl. the original Amiga code as reference |
| `tools/asn_live.py`, `asn_cold.py`, `asn_abtest.py` | Hatari tests: snapshot WAV record / compare / cost, cold boots (HD, floppy, any machine), pixel gate |
| `tools/mw2patch.py` | the stock tool plus the bank delivery (HD splice + `FILES/ASNBANK.BIN`, floppy payload+bank) when `MW2_BANK=build/asn_bank.bin` is set; an `asn_*` build without it is refused |
Build: `python3 tools/asn_build.py` then `MW2_BANK=build/asn_bank.bin python3 tools/mw2patch.py build [--floppy] --only <default set> asn_core asn_wd asn_lvc asn_lv1 asn_lv2 --out build/asn_hd`.
`mw2patch.py verify` (the stock tool) reports ALL OK with the five patch files in the tree.

Design summary: gating on the first tick (`asn_init0`): bank header `'ASN1'` present and its address word = `$BB000`, a 68000 (the index-register scale probe of `jag_poll`: a 68020+ = TT / Falcon keeps the YM, the
TT because `$5a0` cannot be trusted on a HD TT and the Falcon's DMA does not play 6258 Hz in Hatari, see Hunter's notes), and `tst.b $ffff8901.w` answering under a bus-error guard (ST / Mega ST: no DMA sound -> YM).
In mode 2 the original tick is never run: the first tick of a session silences the YM once (`$ff8800`: mixer register 7 |= `$3f`, volumes 8-10 = 0: the title music's `$d0e` driver may have left notes on) and sets the Microwire once
(master 40, L/R 20, bass/treble 6, mix DMA+YM, guarded, copied from Hunter). Requests: `$6862` / 6 -> id -> row `BANK+$100+8*id`; sustained `$686c` re-requested when all four voices are idle; level `$19218` (2..9).
Voices: Amiga's 22-byte records plus phase/increment (`$20`-byte slots at SV+`$40`), mixer: nearest-neighbour phase `inc16 = (K4 / period) << 2`, `K4 = 9285653`, period clamped 142..2000, `(a0,d0.w)` byte fetch,
256-byte volume table lookup (16 levels = (volume >> 8 + 2) >> 2; gain set 0 = half scale for up to 2 audible voices, set 1 = quarter scale for 3-4, so a sum never overflows 8 bits), first voice stores, the others add;
loops wrap after each call (`idx -= length` while `>=`; the pad covers one call: at most 31 groups of 8 samples x increment 3.99 < 800 B). Ring `$BC000-$BC3FF`, DMA `$ff8901 = 3`, `$ff8921 = $80` (mono 6258 Hz), stopped after 12 silent VBL.

## 6. Evidence (raw outputs, this session)
1. `mw2patch.py verify`: **ALL OK** (stock tool, with the five asn patches present).
2. Unicorn (`tools/asn_test.py unit --ticks 300`):
```
driver: 123 sound/level runs x 300 ticks, mismatches 0
mixer : 60 trials, mismatches 0
amiga : the original Amiga driver vs the blob, 41 sounds x 3 levels x 300 ticks, mismatches 0
```
   Negative control (`ASN_NEG=1`, blob level +1): `amiga : ... mismatches 57`. The "amiga" check executes the ORIGINAL `$2f3b2` of `MWII` and compares AUDxPER / AUDxVOL / AUDxLC (as a pool offset) / AUDxLEN with the
   blob's voices after every tick, with retriggers (a second sound at a random tick) and a sustained re-request. The mixer check compares the 1024-byte ring and the voices' phase after each call with an integer model.
3. Snapshot WAV (Hatari DMA stream, `tools/asn_live.py record t1 --snap raid_jeep_dhafra --quiet --inject 2@2 4@5`; `compare` = |correlation| of the capture (one sample per 8 of the 50066 Hz stream) with the model's render):
```
sound  2: onset  -60 ms after request, |rho| 0.9957 (phase 5, sign -)
sound  4: onset  -63 ms after request, |rho| 0.9926 (phase 5, sign -)
work/snd/t1.wav: sound  2.15s -  2.65s ; sound  5.00s -  5.90s   (25 ticks = 0.50 s, 43 ticks = 0.86 s)
```
   (the sign is Hatari's DMA inversion; the offset is the capture's start lag.) Natural engine: `raid_jeep_dhafra` DMA control `$ff8901 = 03`, voice 3 `vol 47 per 440`, DMA `00` after the sounds ended.
4. **Pixel gate** (`tools/asn_abtest.py --only asn_core asn_wd asn_lvc asn_lv1 asn_lv2 --flips N`, default snapshots, the stock set without tick/p3b/p5; gate = the 32000 visible bytes of both buffers):
```
--flips 10  1mb_ingame_walking: pixels IDENTICAL; fps base 3.1 (63 flips) -> patched 3.2 (64 flips)
            1mb_ingame_foot: pixels IDENTICAL; fps base 4.2 (85 flips) -> patched 4.0 (81 flips)
--flips 40  1mb_ingame_walking: pixels IDENTICAL; fps base 2.8 (56 flips) -> patched 2.5 (50 flips)
            1mb_ingame_foot: pixels IDENTICAL; fps base 4.2 (84 flips) -> patched 4.0 (80 flips)
negative control (same set + test_sky), --flips 10:
            1mb_ingame_walking: pixels DIFFER (36640 bytes); 1mb_ingame_foot: pixels DIFFER (34888 bytes)
```
   (these runs were made with the first layout of the blob, bank inside the payload; the final layout only moves the code: re-run results at the end of this section.)
5. **Cold boots** (`tools/asn_cold.py`; the 3D view = `$6220 = d`, `$700a = 2`, MWPO; the bank/blob compared with `build/asn_bank.bin`; `work/asn_cold/NAME.txt`):
| build / machine | MWPO | 3D view | bank+blob vs file | SV mode | DMA | engine id seen | blob cycles/VBL |
|---|---|---|---|---|---|---|---|
| HD, STE TOS 1.62, 1 MB | yes | yes | 0 bytes differ | 2 | `$ff8901 = 03` | 21 (record `$312`, voice 3) | 8064 |
| HD, Mega STE TOS 2.06, 4 MB | yes | yes | 0 | 2 | 03 | 21 | - |
| floppy, STE TOS 1.62, 1 MB | yes | yes | 0 | 2 (from the moment the game installs its sound tick, `$5138` `$d0e` -> `$18f92`, a few seconds after `$6220 = d`) | 03 | - | 8062 |
| HD, plain ST TOS 1.04, 1 MB | yes | yes | 0 | **1** (YM), `$ff8901` never written | - | YM audible: WAV rms 1480 engine, 7000+ bursts at the injections | 157 |
| HD, TT TOS 3.06, 4 MB | yes | yes | 0 | **1** (YM), DMA 00 | - | - | - |
   The floppy and HD builds carry the default set + the five asn patches. Injected requests (`$6862` = id * 6 at 5, 8, 11, 14 s: ids 2, 4, 12, 40) appear as bumps in the 0.25 s RMS
   series of the STE/Mega STE captures at 5.2, 8.2, 11.2, 14.2 s on top of the engine (`work/asn_cold/hd_mste206_4mb.wav`); on the ST the same requests make the YM bursts. A scripted weapon fire
   (`$6872` pulse) did not launch a shot in the helicopter (only the engine id 21 was seen), so the game's own weapon-fire trigger of ids 1-4/10/39/40 was NOT exercised live (injected requests were).

   Final-layout pixel gate (blob in the bank file, `tools/asn_abtest.py`, same set): `--flips 10`: walking IDENTICAL (3.1 -> 3.2 fps), foot IDENTICAL (4.2 -> 4.0); `--flips 40`: walking IDENTICAL
   (2.8 -> 2.5), foot IDENTICAL (4.2 -> 4.0). The gate is not vacuous: on these two snapshots the blob runs (`asn_live.py cost --live`: 7791 / 7787 cycles per VBL = the natural engine).
6. WAV captures are in `work/snd/` and `work/asn_cold/` (git-ignored). Previews of the whole Amiga list rendered by the model (6258 Hz mono, 3 s each): `python3 tools/asn_build.py wav alt/amiga/wav`.

## 7. What to listen for on a real STE / your Hatari
- Engines (helicopter, jeep, boats ...): a continuous, dull, buzzy loop (not the YM's beep tone) whose pitch follows the vehicle speed through the Amiga's level (2..9) steps; each step of the pitch is audible
  because the game updates the level at its own 5 Hz rate.
- Weapon launches / "unit near" (ids 1-4, 10, 12, 39, 40): short Amiga one-shots (0.4-2 s). Expect them to be duller than on the Amiga: 6258 Hz keeps only 3.1 kHz, the Amiga sounds are up to 14 kHz.
- Loudness: one voice is half scale (-6 dB), 3-4 voices quarter scale; the Microwire is set to 0 dB master, treble/bass flat on the first session (an STE's reset state of the LMC1992 was not checked).
- Plain ST, Mega ST, TT, Falcon: the original YM sounds, unchanged.
- Titles, menus, hall: the YM music as before (the tick is only the 3D view's; a stuck DMA loop must not survive leaving the 3D view: the watchdog stops it within 2 VBL).
- A slowdown of the 3D view of about 5 % (one voice) to 9 % (three voices) while sounds play.

## 8. Unproven / risks (do not flip `default: yes` before these are looked at)
- **Real STE hardware: nothing ran on it.** Hatari only (DMA position read with `movep.l`, `$ff8921 = $80`, the Microwire sequence: copied from Hunter's untested-on-hardware code).
- The game's own weapon-fire triggers (ids 1-4, 10, 39, 40) and id 12 were not exercised by a real shot in the game (the scripted fire did nothing in the helicopter); they were injected through `$6862`
  exactly as the game writes it. The vehicle engines other than the helicopter's (id 21) and the jeep snapshot's (voice 3, `per 440`, `vol 47`: ids 30/32/34 in the model) were not heard live; ids 5-7, 9, 11, 13-15, 18, 38 are not triggered by the ST code at all.
- The engine id per vehicle type is the ST's table (`$732c`); the Amiga's own table (filled at run time) was not read: if the Amiga numbering of ids 17-37 differed from the ST's, engines would sound like the wrong vehicle
  [INFERENCE that the data is shared: the 41-row layout, the engine record shape (`base + scale * level`) and the call-site immediates agree].
- Four simultaneous voices were never captured (the 4-channel cost row is "requested", not polled); the mixer itself is bit-exact for 0-4 voices in Unicorn.
- 60 Hz: sound durations unchanged after `w $ff820a $00` (see §3.4) but the emulated refresh change itself was not verified.
- HD delivery depends on `FILES\ASNBANK.BIN` being present next to the images and on the splice at RUNME text `$46`; a RUNME other than the shipped unpacked one (md5 of `work/dumps/RUNME_unpacked.tos`) is refused by the tool's asserts.
- TT / Falcon: deliberately YM (a 68020+ is refused). TT cold boot proves the passthrough; a TT DMA mode was not attempted (`$5a0` cannot be read to tell a TT from a Falcon on a HD boot, see core.s).
- The bank region `$BB000-$D5E9E` was shown intact through the boot screens and the 3D view on five cells; other screens (War Room, vehicle changes, campaign creation) and 2 MB machines were not walked.
- The whole thing costs real frame rate on the 5 fps game; whether the user prefers that is the user's call.

## 9. For the lead
- Shared files NOT touched: `tools/mw2patch.py`, `tools/abtest.py`, `patches/README.md`, `patches/PATCHES.TXT`, `patches/FLOPPY.TXT`, `skill://mw2-patching`. The private copies `tools/mw2patch_asn.py` / `tools/asn_abtest.py` carry the
  delivery changes (a 68-line diff, `diff tools/mw2patch.py tools/mw2patch_asn.py`). To merge: `MW2_BANK`-style optional bank (HD splice + `FILES/ASNBANK.BIN`, floppy payload+bank on track-sides 81-), and make the stock `build` refuse `asn_*` without a bank.
- Blob map: nothing new in `$B3000-$BAFFF` (the five sites jump into the bank file); RAM `$BB000-$D5E9E` is now taken by the bank (state `$BBE00-$BBEFF`, ring `$BC000-$BC3FF`, blob `$D5600-$D5E9E`).
  Note for the skill: the blob map in `mw2-patching` is out of date (p7_cell_pre, p7_skip_render and p3cp_keys occupy `$B5800-$B7E1C`).
- `.gitignore` covers everything created (`alt/`, `build/`, `**/*.wav`, `**/*.png`); the `work/asn_cold/*.txt|json` logs are small and may be committed or not.
- Suggested text if it ships: PATCHES.TXT / README "what you get": "- Amiga sound effects on an STE / Mega STE: the weapon and engine sounds of the Amiga version through the STE's DMA sound (mono, 6258 Hz, mixed in software)
  instead of the YM beeps. Needs `FILES\ASNBANK.BIN` (built from your own Amiga disk by `tools/asn_build.py`; not included). Costs about 5-9 % of the frame rate while sounds play. ST, Mega ST, TT, Falcon: unchanged."
