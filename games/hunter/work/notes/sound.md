# Hunter: sound effects, ST YM driver vs Amiga samples, STE DMA feasibility

Evidence tags: **[obs]** observed in Hatari or in a RAM dump; **[disasm]** read from disassembly or data; **[meas]** measured in an emulator micro-benchmark; **[INFERENCE]** not verified.
No Amiga data is stored in git: `tools/amiga_extract.py` reads the user's ADF (`alt/amiga/`, git-ignored) and writes WAVs to `alt/amiga/samples/` (git-ignored).

## 1. ST side

### 1.1 Driver and call path
- The ST sound driver is file `FILES/4` (1700 bytes), loaded to **$10FB2** (`$7F44` holds the pointer, `$7F48` its size $6A4) [obs: A0=$10FB2 at every trigger hit; dump `work/dumps/ram_demo_sound.bin`]. `FILES/0` is a 70000-byte RAM image: the driver and music copy plus a save-state tail (`...NTER SAVES 1.1`); not a clean concatenation (47 state bytes differ).
- **Update routine**: VBL vector $70 = **$C5F0**. Its sub `$C628` = `btst #7,$93(a5); beq rts; movea.l $7f44(pc),a0; jmp $40(a0)` (bytes `082d 0007 0093 6708 207a b912 4ee8 0040 4e75`) [obs in dump]. The driver runs once per VBL (50 Hz). Entry +0 = init, +$40 = update.
- **No timer is involved.** In the 3D view (demo) IERA=$00, IMRA=$00, TACR=$00, IERB=$40 [obs, `m $fffa07`], so timers A/B/C/D are off. About 2550 cycles per VBL, 1.8% of CPU, are spent in the driver [obs, Hatari profile over 250 VBL, total 141k cycles per VBL].
- **PSG access** (`$ff8800`/`$ff8802`): only inside the driver. Absolute.l references in the 1 MB RAM image are at driver offsets `$24/$2e/$38`, `$15c..$178`, `$2fa..$318`, `$368` (init and volume writes). They are `move.b #7,$ff8800` + read-modify-write of the mixer, `move.l ..,$ff8800` for tone/noise/volume register pairs.
- **No STE DMA register is referenced** anywhere in RAM ($ff89xx absolute.l scan) [obs].
- **Trigger API** [disasm, confirmed live]. Routine `$AEF6..$AF36`:
  - Entry points: `$AEF6` = effect 6, `$AEFA` = effect 2, `$AEFE` = effect 1, `$AF00` = effect in d4, `$AF0E` = effect in d0, with d1 = channel, d2 = volume.
  - It does `andi #3,d1; a0=*($7f44)+ch; move.b d0,$3d6(a0); move.w d2,$3da(a0+ch)`. So the request byte is `base+$3D6+ch` ($FF = idle) and the volume word is `base+$3DA+2*ch` (0..15, the YM scale).
  - Hit seen: `D0=$11 D1=2 D2=7 A0=$10FB4` at `PC=$AF18`.
  - Channel allocation `$2E18`: 3 channel records at `$1DE(a5)`, round robin. Priority table at `$AF38` = {1,2,2,3,3,3,6,4,4,4,4,4,4,4,4,5,5,5,5,5,5,5}. A lower class steals a higher one; a 50-tick lockout (`$32`) protects a fresh effect.
  - `$AF4E/$AF52` = effect 1 at volume 0 = "stop channel"; `$AF5A` = stop all.
- **Driver internals**: 3 channels (d0 = 2..0). Effect table `$4C8` (16 bytes per record, 21 effects), envelope table `$408`.
  - Record bytes: [0] mixer mode at start (1 tone, 2 noise, 3 both), [1] mode after delay, [2] delay, [3] duration in ticks ($FF = loop until replaced), [4:6] tone period, [6] envelope, [7] flags, [$B..$F] LFO/slide mode.
  - It writes mixer reg 7, tone periods (regs 0..5), noise (reg 6) and volumes (regs 8..10). Same code structure and state layout as the Amiga driver (§2).

### 1.2 Volume and pitch (game side)
- Engine volume = `63 - min(max(|$56(a4)|,|$5A(a4)|)>>7, 63)` >> 2, i.e. **distance based**; the pitch is the **fixed effect pitch** (tone slide modes in the effect record). The ST game code `$2EBE` writes only the volume word `$3DA`, never a period.
- The Amiga main code additionally writes `move.w d0,$2ca(a0)` (period from object speed `$3E(a4)`, `base + (-speed*4)`), so Amiga engines pitch with speed. This is **not** implemented on the ST (nothing to match; optional extra on STE).

### 1.3 Effect IDs (0..20)
How I got the names (all three agree):
- The object type table (52-byte records at Amiga `$D45E`; long at +$24: bits 0-4 = effect id, bits 8-10 = class) gives each *object type* an effect id. The type names are the game's own `*`-separated name list (index = type) in the main file.
- The ST object file `FILES/1` is **byte-identical** to the Amiga `externs/objfile` (0 differing bytes of 65536), so ids mean the same on ST and Amiga.
- Runtime log (Hatari, bp at `$AF18` on the in-game demo, ~190 hits, 16 distinct ids), with the caller from the return address.

| id | what | trigger / evidence | ST YM sim [meas, my simulation of the driver] | Amiga sample, rate, mode |
|---|---|---|---|---|
| 0 | player death ("DEAD" message, class 1) | `$3016` `moveq #0,d4; jsr $af00` [disasm; not seen live] | tone 896-1004, 1.4 s | s0 7474 B, 5834 Hz, one-shot 57 ticks |
| 1 | pickup ping ("You have taken ..."); with vol 0 it is "stop channel" | `$AEFE` callers `$9EE8`, `$A09A`; seen live ret `$9EEC`; vol-0 stops from `$316A/$314E/$7ED6/$AF60` | tone 59, 0.24 s | s1 1528 B, 4183 Hz, 16 ticks |
| 2 | message beep | `$AEFA` callers `$4680 $8BF8 $AE6E`; seen live ret `$8BFC` | tone, 0.28 s | s2 1638 B, 5834 Hz, 32 ticks |
| 3 | big explosion (types Ab, Gb) | via object `$2DEC`, seen live | tone+noise, 2.9 s | s3 11782 B, 4183 Hz, 128 ticks |
| 4 | medium explosion (Am, Gm) | seen live | tone+noise, 1.6 s | s3 @6300 Hz, 96 ticks |
| 5 | small explosion (A, As, Gs) | seen live | tone+noise, 1.1 s | s3 @8365 Hz, 64 ticks |
| 6 | bullet / tracer / "Zap" | types 82, 95, 103 [disasm]; seen live | noise burst 0.54 s | s4 5494 B, 8365 Hz, 32 ticks |
| 7 | tank engine (both tanks) | seen live | low tone 2829-3340 | s5 LOOP 6186 B, 3963 Hz |
| 8 | armoured car engine | type 15 [disasm], not seen live | tone | s5 @4975 Hz LOOP |
| 9 | truck / ambulance engine | types 0, 2 [disasm], not seen live | tone | s5 @5961 Hz LOOP |
| 10 | scanner van / gunboat / jeep engine | types 11,12,13; seen live | tone | s5 @7917 Hz LOOP |
| 11 | car / rocket boat / ship / hovercraft engine | types 1,8,9,14; seen live | tone | s6 LOOP 7272 B, 7051 Hz |
| 12 | light aircraft / "amphiunisuperduperbigmobile" | types 7, 18 [disasm], not seen live | tone | s6 @9408 Hz LOOP |
| 13 | helicopter rotor (both) | seen live | noise, volume toggles every VBL = 25 Hz chop | s7 LOOP 10684 B, 8365 Hz |
| 14 | shell/missile in flight (bazooka shell, SAM, 80 mm) and flare/SPU burn | seen live | noise 24-28 | s8 LOOP 8388 B, 4183 Hz |
| 15 | ASM / torpedo / laser bolt in flight | types 88, 92, 94 [disasm], seen live | noise 18-22 | s8 @5262 Hz LOOP |
| 16 | no trigger found anywhere | none in types or code [disasm] | noise | s8 @6300 Hz LOOP |
| 17 | player "tired" breathing (low stamina), repeats every 300 VBL | `$AEA4` -> `$AF0E`, delay table `$AE28` | noise swell 3.8 s | s11 7678 B, 3464 Hz, env 2, 224 ticks |
| 18 | same, other stamina band | same | tone+noise 3.2 s | s10 1428 B LOOP, 1732 Hz, env 2, 254 ticks |
| 19 | door / hatch / lift state toggle | `$2C9A moveq #$13,d4; jsr $af00` (object bit $A flip, swaps $24/$90); seen live ret `$2CA2` | tone+noise 0.84 s | s11 @8268 Hz, 224 ticks |
| 20 | seagull (bit 31 type 20) | seen live | tone 90-344, 1.9 s | s9 1604 B LOOP, 4524 Hz, 16 ticks |

"Not seen live" = identified statically only; the demo never produced it.
The runtime log shows up to **3 channels busy at once** (e.g. VBL 39663: explosion + shell + stop).

### 1.4 Music
**There is no in-game music on the ST.** [obs] Timers off in the 3D view; the VBL handler calls only the effect driver. The YM music (`FILES/3`, a 66.6 KB program incl. tunes) is only used by `jsr $c976` (title tune, loops until space, scancode $39) and two other screens (`$93F0`, `$948C`). The Amiga mirrors this: VBL runs `jmp $4a(a0)` (sfx) if bit 7 of `$99` is set, else the music `jmp $94(a0)`. `$98(a5) bit 7` marks music loaded.
=> an STE DMA replacement does not touch music. The DMA stream must be stopped whenever the game leaves the 3D view (`$93 bit 7` clear), so YM music is not accompanied by a stuck loop.

## 2. Amiga side
- ADF = bootblock-loaded custom trackloader, **no AmigaDOS filesystem** (rootblock invalid). Bootblock (`$0C..`): loads 4 tracks (offset `$14A00`, step `$2C00`) to `$30000`; `jsr` = Fairlight packer + intro; reads 14 tracks to `$40000` and jumps; the crack menu (hunk image) at `$20000` is run in between.
- The game main (14 tracks, 71680 B) copies itself to `$800`, jumps to `$1EF6`. Game tracks: number t<80 = cyl t side 0, t>=80 = cyl t-80 side 1; 10 usable sectors (5120 B) per track, the 11th is a dummy [disasm of the trackloader `$10DF6`, `adda #$1400`].
- File table (22 records of 32 bytes at `$10672`): `externs/soundfile` = track 111, 72572 B (table says 14 tracks; the last 892 B of sample 11 sit on track 125 and are **not** loaded by the original loader, so Amiga plays silence there). `musfile` = track 101, 48640 B.
- soundfile layout: code (+0 init, +$4A VBL update), state `+$2D2`, sample offsets (16 longs) `+$2EE` (relative to `+$580`), per-sample 6-byte records (len words, loop offset, loop words) `+$35E`, envelopes `+$400`, 21 effect records (sample, envelope, period word, duration; 16 B each) `+$430`, sample data (8-bit signed PCM) `+$580`. Amiga driver has 4 channels, the same request/priority/lock logic as the ST driver; effects table order = ST effect ids (same 21 entries; loops exactly the id set 7..16 on both).
- `tools/amiga_extract.py` extracts everything (see §2.1), tested.

### 2.1 Samples (WAVs in `alt/amiga/samples/` and `effects/`)
All PCM is 8-bit signed; PAL rate = 3546895/period. 12 samples, **71156 bytes** total at the original rate.

| sample | bytes | native rate(s) | mode | effect ids |
|---|---|---|---|---|
| s00 | 7474 | 5834 | one-shot | 0 |
| s01 | 1528 | 4183 | one-shot | 1 |
| s02 | 1638 | 5834 | one-shot | 2 |
| s03 | 11782 | 4183/6300/8365 | one-shot | 3,4,5 |
| s04 | 5494 | 8365 | one-shot | 6 |
| s05 | 6186 | 3963/4975/5961/7917 | loop | 7-10 |
| s06 | 7272 | 7051/9408 | loop | 11,12 |
| s07 | 10684 | 8365 | loop | 13 |
| s08 | 8388 | 4183/5262/6300 | loop | 14,15,16 |
| s09 | 1604 | 4524 | loop | 20 |
| s10 | 1428 | 1732 | loop | 18 |
| s11 | 7678 | 3464/8268 | one-shot | 17,19 |

Sizes if resampled [computed]:

| | original | @12517 Hz | @6258 Hz |
|---|---|---|---|
| 12 unique samples (each at its first effect's rate) | 71156 | 183643 | 91814 |
| all 21 effect variants prerendered | 145004 | 320931 | 160453 |

Native rates are 1.7-9.4 kHz, so 6258 Hz output (Nyquist 3.1 kHz) already loses the upper band of ids 5, 6, 12, 13, 19; 12517 Hz keeps everything.

## 3. STE design

### 3.1 Concurrency
The game allocates **3** channels; the demo log shows 3 busy at once but usually 0-2 audible. DMA is a single stream, so a software mixer is needed for fidelity; the fallback is one voice by priority (cheapest).
**Measured mixer cost** [meas: vasm + Musashi, 250 samples, 68000 instruction timing only, no bus wait states]:
- voice store 40.5 cyc/sample, voice accumulate 44.4, voice with 256-byte volume table 58.5, fused 2 voices (32-bit phase) 74.2.

| design | cyc/sample | CPU at 12517 Hz | at 6258 Hz |
|---|---|---|---|
| 2 voices, no volume | 85 | 13% | 6.6% |
| 2 voices, volume tables | 113 | 18% | 8.8% |
| 3 voices, volume tables | 172 | 27% | 13% |
(% of 8 MHz; the demo already uses ~141k of the 160k cycles available per VBL, so this is a direct slowdown; the mixer only runs for audible voices) [INFERENCE: real STE contention makes it ~5-15% worse].

### 3.2 Loops and pitch
- Loops: the original Amiga effect records give full-sample loops (s05-s10) and one-shots with an 1-word idle loop. A software mixer wraps the phase (split spans per VBL to avoid per-sample bounds checks). DMA hardware loop mode only works for the single-voice fallback.
- Pitch: the ST game never changes pitch, so per-effect fixed steps (period table above) are enough. Resampling by phase step (nearest neighbour = same zero-order hold Paula uses) is the right tool; DMA rate switching has only 4 rates and changes the whole mix. Optional Amiga-style speed pitch cannot be driven from the ST trigger API (only volume is passed).

### 3.3 Memory (1 MB)
Zero runs in the in-game RAM image (demo, and the on-foot snapshot `ram_foot_stand.bin`, same result):
- **$8BA00-$AF000 = 141 KB**, $B8200-$C0000 = 31 KB, $3EE00/$43C00-$48000 = 17-36 KB, plus small holes.
- **Poison test** [obs]: patterns written into $8C000-$AE000, $B8400-$C0000 and $43C00-$48000, ~19000 VBL of demo (explosions, vehicles, boarding): 0 bytes changed.
- Tested on 1 MB STE / TOS 1.62 only; 4 MB layout not examined.
- Fits: native-rate samples 71156 B + driver ~2 KB + volume tables 4 KB + ring buffer ~1 KB in the 141 KB hole. Pre-resampled @12517 does **not** fit (184-321 KB), @6258 fits only as unique samples (92 KB).

### 3.4 Hooking
- Detect STE by **hardware probing** (bus-error-guarded read of $FF8901 or palette bit test), **not** by cookie: in HunterBench's title dump the jar had `_CPU=0, _MCH=0`, no `_SND` (Gamex/HDDRIVER environment).
- **Recommended hook** (leaves the ST path untouched):
  1. Replace the 8 bytes at `$C630` (`movea.l $7f44(pc),a0; jmp $40(a0)`) by `jsr payload; rts` (`4eb9 xxxxxxxx 4e75` = 8 bytes, the `beq` to `$C638` still reaches an `rts`).
  2. The wrapper snapshots the pending request bytes (`base+$3D6+ch`), calls the original `$40(a0)` unchanged, then reads the results: a started effect = a pending request with lock counter `+$C+ch` = $32; ongoing volume = the driver's YM volume image (reg 8+ch) or `$3DA`.
  3. Plain ST: no payload call (YM runs as before). STE: the YM writes of the original driver are redirected to a scratch area (17 absolute.l operands in the driver) so YM stays silent while the state machine (priority, lockout, durations, envelopes) is reused and only the output changes.
- Wrapper does the mix for a window ahead of the DMA frame counter ($FF8909/0B/0D) in a ring buffer, DMA loop mode, mono, 12517 Hz.
- Not yet verified: the YM volume-image to mix-volume mapping, and DMA behaviour in Hatari/real hardware.

### 3.5 Gamex loader and payload delivery (what is known)
- `HUM.FIC` ('C3' header, 71684 B unpacked) = the game main; START.TOS (PP-packed, `pp_depack.py` unpacks it to $82AE text) loads `HUNTER.PCH` (title pictures), `D15R_H5.FIC` (HD loader, 51000 B), `HUM.FIC` (to $81000) and sets memtop to $80000, leaving `PPGX` at memtop. START needs a real FAT HD with the HDDRIVER boot sector, not Hatari's GEMDOS drive (see `hunter.py`).
- The in-game loader (`$108E4` -> `$D30E` -> `$D53A`) reads `FILES\<n>` by name from the FAT disk and takes the size from the main file table (`$7F3C..$7FD0`, 8-byte (ptr,size) pairs, allocated sequentially from $10FB2). It lives inside the compressed HUM.FIC.
- Consequences: (a) to enlarge `FILES/4` the table size in HUM.FIC must be patched (repack or live patch); (b) simplest delivery = a patched START.TOS (it already does GEMDOS Fopen/Fread) that also reads a payload file to $8BA00, then a one-shot RAM patch of `$C630` after HUM is unpacked; (c) START refuses "Too much low RAM" / needs 1 MB. Not tested: any of this.

## 4. Verdict
**Feasible.** The effects are cleanly separable: same API and ids on ST and Amiga, 12 samples / 71 KB, free RAM of 141 KB demonstrated, no music in-game, no DMA conflict, and the VBL call is a single hookable site.
- **Effort**: ~2-3 days: extractor (done), mixer + wrapper in assembly (~300 lines), volume tables, patch/build tool, test on STE/Mega STE/Falcon in Hatari.
- **Risks**: (1) CPU: 3 voices @12.5 kHz cost up to ~27% of an already saturated game; mitigation 6258 Hz or 2 voices; (2) payload delivery through Gamex (HUM.FIC repack vs START.TOS patch) is unproven; (3) STE detection under Gamex cookies; (4) Microwire volume/tone defaults on real STE; (5) ids 8, 9, 12, 16 and 0 not heard live.
- **Recommended design**: shadow driver (keep the YM driver's state machine, mute YM, mix 3 voices from native 8-bit samples with 256-byte volume tables into a mono ring at 12517 Hz, DMA loop), optional 6258 Hz mode and a one-voice zero-CPU DMA fallback when only one sound is active.

## 5. Addendum (from HunterBench, observed during a normal boot to the 3D view)
- Load hook (`$150`, d0 = file hex digit, a0 = destination): file 6 -> $23000, 4 -> $10FB2 (sound driver), 3 -> $11656 (music), 7 -> $79714, 8 -> $2AD00, then 9 -> $2AD00 (overwrites), 1 -> $61514, 2 -> $48004, E -> $23000.
- `FILES/0` is **not** loaded by the time the 3D view runs, so §1.1's remark about it only describes the file's content, not a load step.
- A 4 MB snapshot exists (`work/snapshots/4mb_foot_stand.sav`); the free-RAM map in §3.3 was not repeated on it.
- Always run Hatari with `--joy1 keys` (`Hunter()` does), or the game sees a phantom joystick.
