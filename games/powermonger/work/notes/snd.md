# Powermonger sound: the timer-A sample player and the STE DMA replacement (PMSound)

Patches (all `; default: no`, enable together): `patches/snd_core.s` (sequencer hook `$1b77e` + the whole payload at `$D0000`), `snd_start.s` (`$1ae5c`), `snd_stop.s` (`$1ae36`), `snd_setup.s` (`$11f0`).
Gate tool: `tools/pmsnd.py` (`pairs`, `live`, `cost`, `wav`, `cmp`, `boot`). Evidence: raw output or disassembly (`tools/m68dis.py` on `work/dumps/map_idle.bin` / `entry10a6.bin`); `[INFERENCE]` = not run. Hatari 2.6.1, 1 MB STE, TOS 1.62 unless stated. WAVs: `work/snd/*.wav` (git-ignored).

## 1. The original player

**There is no other sound.** The game proper writes the YM only in `$1aeb0` (all tone/noise/volume registers 0, mixer = off), the sample IRQ `$1af32`, and port A (drive select: `$de50`, `$1bf2e`). No tone/noise effects, no music in the game proper (`DATA\SPRITE40.DAT`). The title/intro program (stage 1) has its own code: not examined; the patches only touch stage 2.

### 1.1 The IRQ `$1af32` (MFP timer A, vector `$134`)
```
01af32  move.w d0,-(a7) / move.l d1,-(a7) / move.l a0,-(a7)
01af38  movea.l #$5ddd2,a0                     ; the immediate is the stream pointer, rewritten at $1af3a
01af3e  clr.w d0 / move.b (a0)+,d0 / beq.b $1af6c      ; byte 0 = end of the chunk
01af44  move.l a0,$1af3a.l                      ; save the pointer
01af4a  lea.l $fa0f.w,a0 / lsl.w #3,d0
01af50  move.l $1af86(pc,d0.w),d1 / move.w $1af8a(pc,d0.w),d0       ; 8-byte entry: reg 8,v8,reg 9,v9,reg 10,v10,0,0
01af58  movep.l d1,-$720f(a0) / movep.w d0,-$720f(a0)               ; $ff8800/02/04/06: YM volume A, B, C
01af60  bclr.b #5,(a0) / (restore) / rte
01af6c  move.b #0,$fa19.w / sf.b $2c993.l / bclr.b #5,$fa0f.w / rte  ; end: timer off, busy flag cleared
```
* 264 cycles per interrupt [hotpaths.md: 568 IRQs = 150 146 cycles per pass]. Timer A: `$fa19 = 1` (delay mode, /4), data byte `d = $2c99a` (`$1ae82`): **rate = 2 457 600 / 4 / d = 614 400 / d Hz**.
* Cost = rate x 264 cycles: 2.4 kHz = 8 %, 5 kHz = 16 %, 8.1 kHz = 26.7 % of an 8 MHz CPU. Measured on `map_idle` (sequence 3, chunks at 8084 Hz): **26.41 %** of all cycles (5 115 760 cycles in `$1af32-$1af85` over a 120-VBL window, 19 270 IRQs; 42 631 cycles per VBL); at 16 MHz 13.17 %.
* Setup `$1adcc` (once, `$110a`+): `bsr $1aeb0`, saves `$134`, stream pointer = `$1b7fa` (a 0 byte), timer A data `$2c99a`, `$134 = $1af32`, enables timer A (IER/IMR bit 5). `$1ae5c` starts a chunk: pointer = `[$2cba6 + 12*$2c998]`, `$fa19 = 0`, data = `$2c99a`, `$fa19 = 1`, `st $2c993` (busy). `$1ae36` stops: pointer = `$1b7fa`, then waits for `$2c993 = 0`. `$1ae4c` (shutdown) = stop + restore `$134`.

### 1.2 The data format: signed 8-bit PCM, played through a 256-entry YM volume table
* The table at `$1af86` has 256 entries of 8 bytes, **indexed by the sample byte itself** (entry `b` at `$1af86 + 8b`, `b` = 0..255; entry 255 lies on the code after the table, `$1b77e`: a sample byte 255 (-1) writes garbage to the YM; harmless, a game bug). Each entry holds three 4-bit volumes (regs 8, 9, 10: the three channels summed, chosen so the sum approximates a linear ramp).
* Mapping, fitted with the measured ST 3-channel table (Hatari `src/includes/ym2149_fixed_vol.h`, 0..65535) over `s = b` (signed, -127..127): **A(s) = 18 692 - 146.6 s**; residual std 554 (= 3.8 LSB of 8 bit), max 2 799; for -128: 38 145 (3 x 15, the clip). So the bytes are linear signed PCM and the YM output is an *inverted* quantised copy of them.
* The STE LMC1992 inverts the DMA signal as well (Hatari `dmaSnd.c:534`), so **the bytes can go to the DMA unchanged and the polarity agrees with the YM path** (Hatari capture: correlation `+0.96..+0.99`; an in-place negation was tried first and gave `-0.96`).
* FX.DAT (resource 9, packed 75 544 B) is unpacked to `$5879a` (`$16b6a` bytes, end `$6f304`). `$1b83c` (called at `$11ea`, once at game start) reads its header: word at +0 = 58 (chunks), +2 = 56 (sequences), then a long offset table; it fills the sequence pointers `$2c9a0[k]` (56 x 4) and the **chunk table `$2cba6`: 12 B per chunk {start, start, length}**, 58 entries. Each chunk is `n-1` sample bytes plus ONE 0 byte (the player stops at the 0, the table length is not used by the player; the table's last entry is bogus (length 7 774 529): the real length is `$6f304 - start` = 2867). 57 zero bytes in 57 chunks; no zero inside a chunk.
* Sizes: chunks 24..5328 B, 78 714 B of samples in total; chunk 5 (24 B of byte 1 = silence) is the timing filler (see 1.3).

### 1.3 Sequencer: `$1b77e` (called from the VBL handler `$1282` whenever `$2de66 != 0`)
```
01b77e  tst.b $2c992.l / beq.w $1b7ee                    ; sequence active?
01b788  tst.b $2c993.l / bne.w $1b7ee                    ; the previous chunk is still playing (timer IRQ busy)
01b792  move.w sr,-(a7) / move.w #$2700,sr / movea.l $2cba2.l,a0 / move.w $2c996.l,d0 / add.w d0,d0
01b7aa  d1 = (a0,d0.w) chunk, d2 = 1(a0,d0.w) timer data;  d1 == $ff -> loop ($2c994) from step 0, else sf $2c992 (done)
01b7d2  addq.w #1,$2c996.l / $2c998 = d1 / $2c99a = d2 / jsr $1ae5c.l / move.w (a7)+,sr / rts
```
* A **sequence** (56 of them, pointers `$2c9a0[k]`, bytes in FX.DAT at `$5896a..$5bf8a`) is a list of 2-byte steps {chunk, d} ended by chunk `$ff`. Steps start **only at VBL ticks**, after the previous chunk's end (IRQ clears `$2c993`), so chunk starts are quantised to 20 ms.
* Timing is built from that: the rate `d` is tuned so that a chunk ends just before a VBL (651 B at 8084 Hz = 80.5 ms = 4.03 VBL), and **chunk 5 at d = 245/255 (24 B at 2508/2409 Hz = 9.6-10 ms) is a one-VBL pause** (e.g. effect 2: 1364 steps, 1269 of them pauses). The same chunk is also played at **different rates per step = pitch changes** (effects 7..12 = chunk 18 at 4690, 5437, 5796, 6269, 6678, 8192 Hz; effect 1 = chunks 0-4 at 3200..8084 Hz).
* 381 distinct (chunk, d) pairs in 6872 steps; source rates **2409..8654 Hz** (median by playing time about 5.1 kHz).
* One voice: a new sound starts in `$1b978(seq ptr, flags)` (`flags & $80` start, `& $20` loop = restart at the `$ff`, `& $10` = "is one active?" query in `$1b9d0`): it clears `$2c992`, calls the stop `$1ae36`, sets `$2cba2` = pointer, `$2c996 = 0`, `$2c994` = loop, `$2c992 = 1`. **There is no overlap or mixing: a new effect cuts the old one** (so one DMA voice is exact; a 2-voice mixer would have nothing to mix).

### 1.4 Triggers and the effect list
Game code does not call the player directly. It raises a pending word `addi.w #1,<record>` in the effect table (64 records x 14 B at `$1291a`; words {pending, lockout.l (+2), effect id (+6), volume class by zoom (+8, not used by the player), priority (+10, lower = better), flags (+12, `$a0` = loop, `$80` = once)}) at about 25 sites (`$11d36 $117c4 $11750 $150c2 $16094 $50ec $5162 $11a88 $11b3e $25e2 $6ea0 $25ea $53d8 $11cec $11c54 $3e5e $11b32 $53cc $13608 $136a0 $13b7c $11c42 $11c66` and more via `$1ba3e` direct calls at `$126ea..$127b0`, `$76e6`). `$127e6` (world logic call `$13040`, once per pass; once per tick with the tick patches) picks the best pending record by priority, honours the lockout (`$6f304`-based) and calls `$1ba3e(id, flags)` = `$1b9d0` -> `$1b978`. Ids 57-64 have no sequence (ignored).

| ids | priority | kind | sequence | notes (role is [INFERENCE] from the use sites and durations) |
|---|---|---|---|---|
| 1-4 | 99 | loop | 17-55 s, chunks 0-4 / 12 (7.8-8.1 kHz); 4: chunks 0,1,2,6,11,12 at 2.4-3.4 kHz | ambient loops (`$126ea`: id = season `$57fd0/2 + 1`) |
| 5, 6, 13, 14 | 9 | loop | 3-11 s, many pause steps + chunks 13-17, 20, 21 | |
| 7-12 | 7 | loop | 0.7-1.65 s, chunk 18 at six pitches | the same voice/shout at different pitches |
| 15-18 | 9 | loop | 4.8-15 s, chunks 22-29 | |
| 19, 27, 28 | 10 | loop | 19-21 s, chunks 35, 36 | |
| 20, 21 | 4 | once | 0.21 / 0.23 s, chunks 37, 38 | short effects |
| 22-24, 29, 30 | 10 | loop | 0.26 s of pure pauses | silent placeholders |
| 25, 26 | 10 | loop | 10-14 s, chunks 41, 42 (+pauses) | |
| 31-36 | 2 | once | 0.22-0.38 s, chunks 43, 44 | |
| 37, 38, 55, 56 | 8 / 6 | loop | 3-13 s, chunks 45-48 (up to 8654 Hz) | noise-like (battle?) |
| 39-41 | 7 / 1 | loop | 0.5-1.1 s, chunks 49, 19, 20, 47 | |
| 42, 43 | 10 | loop | 8-10 s, chunks 50-53 | |
| 44-46 | 1 | loop | 0.46-0.85 s, chunks 54, 55 | highest priority |
| 47-50 | 3 | once | 0.43-0.8 s, chunks 39, 40 | |
| 51, 52 | 3 | once | 1.0-1.4 s, chunk 56 + pauses | |
| 53, 54 | 6 | loop | 1 s, chunks 19, 57 | |
(generated from the `entry10a6.bin` records and the `map_idle.bin` sequences; "loop" = the record's flag `$20`.)

## 2. The replacement (STE-class DMA, FLAGS bit0)

### 2.1 Why not a static bank
The step rate `d` varies per step (381 pairs), so a sample must be replayed at its own rate. Pre-resampling every pair to the STE DMA rates would cost **528 KB at 6258 Hz / 1057 KB at 12517 Hz** (`pmsnd.py pairs`), and the DMA only offers 6258/12517/25033/50066 Hz. So the chunk is resampled **live** (nearest neighbour = the same zero-order hold the YM player has) into a staging buffer, **one VBL ahead of the DMA read pointer**, and played through a single-shot DMA frame. The alternative "direct" mode plays the chunk bytes unchanged, zero CPU, wrong pitch (3.2).

### 2.2 Hooks (4 sites, all stage 2; the ST path runs the original instructions, so plain ST is unchanged)
| site | orig | new | what |
|---|---|---|---|
| `$1b77e` | `tst.b $2c992.l` | `jsr $d0000.l` | every sequencer call: STE: if a DMA chunk is busy, keep the producer ahead and clear the busy flag `$2c993` when the DMA has stopped (`$ff8901` bit 0 = 0) = what the IRQ's end did; then `tst.b $2c992.l ; rts` (the original flags) |
| `$1ae5c` | `lea.l $2cba6.l,a0` | `jmp $d0004.l` | chunk start (STE: DMA; ST: `lea ... ; jmp $1ae62`) |
| `$1ae36` | `move.l #$1b7fa,$1af3a.l` | `jmp $d0008.l` + 2 nop | stop (STE: DMA off, `$2c993 = 0`; ST: displaced move + `jmp $1ae40`) |
| `$11f0` | `addq.l #8,a7 ; move.w #1,$2de66.l` | `jsr $d000c.l` + 2 nop | game start, after `$1b83c`: Microwire (master 40 / L,R 20 / mix DMA+YM / treble-bass flat, bus-error guarded, from Hunter), `DEFMODE`, the two displaced instructions, `a7` as after the addq. The timer-A set-up `$1adcc` is left alone: it fires one IRQ at the silent stream and stops; **timer A is never started again on STE (IRQ off, CPU free)**. |

### 2.3 The producer (blob `$D0000`, state `$D0E00`, staging `$D1000-$D4FFF`: 16 KB `; data:` span, zeroed at boot, no disk bytes)
* Start (`snd_start`): chunk = `$2c998`, `d = $2c99a` (0 = 256). Length clamped to `$6f304 - start`. **DMA rate = 12517 Hz if the source rate is above 6258 Hz (`d < 99`), else 6258 Hz** (the DMA is never below the source rate, so the 16.16 step stays below 1 and each output sample is one `add.w/addx.w` of a phase). `step = K / d` (K6 = 6 433 916, K12 = 3 216 958 = 614400 * 65536 / rate), output count `M = (n-1) / step` rounded down to a multiple of 8 (<= 7 samples = 0.6 ms shorter), the first 512 samples are made before the DMA starts (DMA: `$ff8921` mono + rate, start/end, `$ff8901 = 1`). The busy flags `$2c993` and SV are set.
* Producer (each VBL while busy): reads the DMA address counter (`movep.l` twice until stable), makes samples up to position + 768 (nearest neighbour, 8 per unrolled step, about 31.7 cycles per sample all in), at SR `$2500` (MFP interrupts stay open, the VBL cannot re-enter). The DMA ends by itself at `STAGE + M`; the next VBL tick sees `$ff8901` bit 0 = 0 and clears busy; the sequencer then starts the next step exactly as it did after the IRQ's zero byte, **so pauses, VBL quantisation and loops behave as before**.
* **Build option `DEFMODE` (snd_core.s, 0 = default live resample):** 1 = direct DMA of the chunk (`start = chunk`, 6258 Hz, no producer). Poke `$D0E01` (SV+1) to switch live (the gates do).
* "Stop when the game leaves the screens that use it": the DMA is single-shot, so it ends with the chunk; `$1ae36` (a new sound, `$1b81c` game shutdown) turns it off at once. No loop DMA, no interrupt, no state outside SV.
* Size: code about 1.3 KB; floppy payload with the four patches 1296 B of records; free RAM used `$D0000-$D4FFF` (inside the snd_ range).

## 3. Gates (all raw output)

### 3.1 CPU while a sample plays (`pmsnd.py cost map_idle 8 150 [--orig|--mode 1] --fps-vbls 1000`, 8 MHz, `map_idle` = sequence 3, chunk 12 at 8084 Hz; profile window 120 VBL)
```
orig        : timer-A IRQ 5115760 cycles (19270 IRQs) = 42631 cycles/VBL = 26.41 % of the CPU; fps 2.35 (47 flips / 1000 VBL, 21.3 VBL/frame)
DMA live    : payload   952776 cycles = 7940 cycles/VBL =  4.92 % (6 chunk starts, 120 ticks); fps 3.35 (67 flips, 14.9 VBL/frame)   [final build: 944568 = 4.95 %, fps 3.35]
DMA direct  : payload    31120 cycles =  259 cycles/VBL =  0.16 %;                                                fps 3.60 (72 flips, 13.9 VBL/frame)
16 MHz orig : IRQ 5090860 cycles = 42424 cycles/VBL = 13.17 %; fps 6.30 (126 flips)      16 MHz DMA live: 952608 cycles = 7938/VBL = 2.46 %; fps 7.15 (143 flips)
```
8 MHz map_idle: **+43 % fps (2.35 -> 3.35) with the live resampler, +53 % (3.60) with the direct DMA.** The live producer costs about 31.7 cycles per output sample (12 517 samples/s = 4.9 %; at 6258 Hz 2.5 %). Average over all effects (each step weighted by its playing time; computed from the sequence tables, [INFERENCE] not measured effect by effect): original 18.6 % of 8 MHz (1.49 M cycles/s), live DMA 3.4 % (38 % of the playing time runs at 12517 Hz).

### 3.2 WAV capture, original YM player vs DMA, same trigger (`pmsnd.py wav NAME ID SECS [--orig|--mode 1|--st]`, `pmsnd.py cmp`)
Hatari `--sound 50066` + `hatari-shortcut recsound`, snapshot `map_idle` (the running sequence is cut first), the effect injected by writing the sequencer state at a loop top in both runs (`$2cba2` pointer, `$2c996 = 0`, `$2c994 = 0`, `$2c992 = 1`). `rho` = normalised correlation of the onset-aligned captures after a 9-tap low-pass, best lag within 50 ms; duration = smoothed envelope above 8 % of its peak.
```
effect  what                         rho live   dur orig/live (s)   direct rho   dur direct (s)   centroid orig/live (Hz)
47      1 chunk, 7144 Hz              +0.963     0.443 / 0.439       +0.181       0.504             6213 / 7219
50      2 steps, 5908/6678 Hz         +0.928     0.811 / 0.808       +0.316       0.802             6082 / 6858
44      2 chunks 54, 55               +0.960     0.467 / 0.475       -            -                 5130 / 6004
20      1 chunk 5796 Hz               +0.981     0.178 / 0.179       -            -                 4437 / 5209
7       53 steps (pauses + chunk 18)  +0.988     1.126 / 1.126       +0.078       0.856             3682 / 4269
15      31 steps, 4995 Hz             +0.992     5.238 / 5.235       +0.049       3.995             3764 / 3355
5       483 steps, 10.6 s             +0.974     10.599 / 10.599     -            -                 4979 / 5949
37      431 steps, noise-like, 14.6 s +0.902     14.612 / 14.666     -            -                 6472 / 7243
```
Windowed (200 ms) |rho|: effect 15 mean 0.992 (min 0.979, n = 26), effect 5 mean 0.968 (min 0.879, n = 40), effect 37 mean 0.891 (min 0.729, n = 51; 43 % of its energy is above 3.1 kHz, where the YM's own amplitude quantisation noise is the difference). The DMA capture is about 1.3 x louder (rms 5436 / 4161 in the sound window of effect 47): the YM version only reaches about 0.58 of the 8-bit range, the DMA carries the whole byte. Silent before and after (rms 0.0 in the head and the tail of every capture).
* **Resampler vs original: the same sound** (rho 0.90-0.99, equal durations within one VBL over 14.6 s, onsets within +-20 ms = one VBL phase). **Direct DMA is not**: rho 0.05-0.3, durations -24 % to +14 %.
* Pitch error of the "direct" alternative, from the 381 pairs (`pmsnd.py pairs`): the nearest of 6258/12517/25033/50066 Hz to every source rate (2409-8654 Hz; the geometric midpoint of 6258 and 12517 is 8850 Hz) is **6258 Hz for 100 % of the playing time**; the DMA plays the samples too high by **+492 cents on average (mean |error| 692, max 1653 = 1.4 octaves)**; 8 % of the playing time is within 100 cents, 29 % within 300, 59 % within 600. Durations change by the same ratio (and the pause chunk 5 becomes 3.8 ms instead of 9.6 ms, still under one VBL).
* Plain ST path of the patched build (live image with FLAGS = 6, same trigger): effect 47 `rho +0.9962`, rms 4154 / 4161, duration 0.443 / 0.443; effect 15 `rho +0.9999`, windows min 1.000, duration 5.238 / 5.238 (`e47_st.wav`, `e15_st.wav`).

### 3.3 Cold boots (floppy build `pmpatch.py build --only snd_core snd_start snd_stop snd_setup --floppy --out build/snd`: payload 1296 B of records, free on disk 54272 B)
```
STE 1 MB TOS 1.62 : 3D view in 190 s, MARKER=b'PMPO' FLAGS=0x3; (active, step, chunk, d, $ff8900, SV busy/mode) = (0x1ff, 0x19, 0xc, 0x4c, 0x1, 0xff00) -> step 0x30 two samples later:
                    the ambient sequence plays through the DMA (play bit set, busy ff, mode 0); capture rms 2187.6; step 83 -> 89 in 2 s (VBL 10896 -> 11097)
ST  1 MB TOS 1.04 : 3D view in 203 s, MARKER=b'PMPO' FLAGS=0x6; $ff8900 reads 0xff (bus error on the ST), SV busy/mode 0: the YM path plays; capture rms 1574.2; step 82 -> 89 in 2 s
STE with tick_* + snd_* (11 sites): 3D view in 190 s, PMPO, FLAGS=3, DMA playing, rms 2205.3 (no site overlap)
```
Not run: 4 MB, Mega STE / TT / Falcon, the HD build, real hardware ([INFERENCE] the DMA/Microwire register sequence is Hunter's, which was only exercised in Hatari).

## 4. Limits, risks
* The producer runs inside the VBL handler (sequencer), once per VBL, about 2 ms at most in one go (first block 512 samples = 17 k cycles, then about 250 samples per VBL at 12.5 kHz). If the VBL handler were delayed by more than about 60 ms (LEAD) the DMA would play the unwritten tail of the buffer (stale samples) until the end of that chunk.
* Polarity: DMA inversion is the documented LMC1992 behaviour [Hatari source comment]; not checked on real STE hardware. Nothing audible depends on it.
* Quality: nearest neighbour from 2.4-8.7 kHz to 6258/12517 Hz = zero-order hold, as in the original; the DMA drops the YM's amplitude quantisation (+-3.8 LSB). Linear interpolation would cost about +30 cycles per sample (not built).
* Level: Hatari mixes the DMA about 1.3 x louder than the YM version; the real STE level relative to the YM is unknown [INFERENCE] (LMC1992 mix = DMA+YM, master 0 dB).
* The effect queue and the sequencer are untouched, so the timing stays VBL based (50 Hz exact; a 60 Hz display runs the sounds 20 % fast, as the original).

## 5. Later: higher-quality replacement samples (not built)
* **What a bank would replace:** the 58 chunks (`$2cba6` index = chunk number; 57 are used by the 56 sequences). The sequence tables (which chunk at which rate `d`, pitch steps, pauses) and the effect queue stay the game's own, so a bank only has to provide a better waveform per chunk; the producer already resamples any source rate to the DMA rate, so a bank sample only needs its own native rate.
* **Bank format (proposal):** a flat file `PMSB`, `u16 version`, `u16 count`, then `count` entries `{u32 offset, u32 length (bytes, signed 8-bit mono, no terminator), u16 rate_hz, u16 nominal_d}` indexed by chunk number (length 0 = keep the original chunk), then the data. Built in with `pmpatch.py build --samples FILE`, which places the file at `SAMPLE_BASE` = `$D0000`: the blob occupies `$D0000-$D4FFF` now, so `SAMPLE_BASE` would have to move to `$D5000` (or this blob up); the snd_ range ends at `$DCFFF` = about 44 KB of bank, and the whole floppy payload has about 54 KB.
* **Use:** `snd_start` looks up `bank[chunk]`; if present it takes `src/length/rate_hz` from the bank and sets the step to `(rate_hz / DMA rate) * ((614400 / d) / (614400 / nominal_d))`, so the game's pitch steps and durations are kept; the DMA rate is picked from the bank rate. Longer or shorter replacements change a step's duration; the entry flag would say "keep the original duration" (stretch by the step ratio) or "own duration".
* A user-supplied bank is data and stays out of git (as Hunter's `hunter_snd.bin`).

## 6. Reproduce
```
python3 tools/pmsnd.py pairs                                  # statistics (no emulator)
python3 tools/pmsnd.py cost map_idle 8 150 [--orig|--mode 1] --fps-vbls 1000
python3 tools/pmsnd.py wav e47_orig 47 3 --orig ; python3 tools/pmsnd.py wav e47_dma 47 3 ; python3 tools/pmsnd.py cmp work/snd/e47_orig.wav work/snd/e47_dma.wav
python3 tools/pmpatch.py build --only snd_core snd_start snd_stop snd_setup --floppy --out build/snd
python3 tools/pmsnd.py boot boot_ste --disk build/snd/floppy/powermonger.st --machine ste --tos 1.62 ; ... --machine st --tos 1.04
```
