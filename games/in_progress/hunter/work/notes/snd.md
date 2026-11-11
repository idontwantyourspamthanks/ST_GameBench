# Hunter STE DMA sound (HunterAudio): design, build, evidence

Evidence tags: **[obs]** observed in Hatari 2.6.1 (raw numbers below, tool = `tools/snd_test.py`); **[disasm]** read from disassembly; **[INFERENCE]** not verified.
Files: `patches/snd_core.s` (one patch, `; default: no`, site `$C628`, blob `$8E000..$8EBBA` = 3003 B, state `$8F000..$8F0FF`, ring `$8F800..$8FBFF`), `tools/snd_build.py` (sample bank), `tools/snd_test.py` (tests, captures, cost).
Nothing from the ADF is committed: the bank is built into `build/hunter_snd.bin` (git-ignored), the WAV captures go to `work/snd/` (**not** ignored by `.gitignore`; they contain Amiga sample material, so add `**/work/snd/` before committing).

## 1. What it does
- STE-class machines only (loader probe `FLAGS` bit0 at `$8BFF0`): the YM effects are silenced and the Amiga effects play through DMA sound, **mono, 6258 Hz, 2-voice software mixer**, mixed into a 1024-byte ring in a looped DMA frame.
- Plain ST / Mega ST (`FLAGS` bit0 clear), or no bank (`'HSND'` missing at `$90000`): the payload runs the original tick unchanged (YM plays), cost = one `jmp` + a few tests.
- The original driver (`FILES/4` at `$10FB2`) keeps running as the state machine (request bytes, priority/lock, durations, volume words); only its 16 YM absolute operands are redirected, and my code reads its state after each tick.
- No timer, no interrupt: everything runs inside the existing VBL tick. At 60 Hz the original driver tick and the scan run on world ticks only (5 of 6 VBL), the mixer tops the ring up every VBL: timing.md section 2. The DMA is stopped when the 3D view is left, so the YM title/menu music is untouched.

## 2. Hook and detection
- Site `$C628` (the sound tick, `bsr`'d from the VBL handler `$C5F0` at `$C614`; only caller [disasm `--callers c628`]): `btst #7,$93(a5)` (6 B) becomes `jmp $8E000.l`. The remaining bytes (`beq.b $c638`, `movea.l $7f44(pc),a0`, `jmp $40(a0)`, `rts`) are dead code. The payload does the `btst` itself, so it can see the transition out of the 3D view (the original did nothing there).
- Mode byte `SV+0`: 0 uninitialised, 1 passthrough (original tick), 2 DMA sound. Set on the first call from `FLAGS` bit0 and the bank header (`'HSND'`, version word 2). The loader's own probe is used (bus error safe, register read-back); no second probe here.
- Driver operand redirect (`snd_ympatch`): the 16 `absolute.l` operands `$ff8800`/`$ff8802` inside the driver (offsets `$24 $2e $38 $15c $162 $16e $174 $17c $2fe $304 $314 $31a $34c $354 $36c $378`, from a disassembly of the whole of `FILES/4` and a raw scan for `00ff880x`: 16, not the 17 of sound.md §1.1) point at a scratch long `SV+$30`. Checked every tick (one `cmpi.l` on the first operand) so a reloaded driver is patched again. The driver's YM readback (`move.b $ff8800,d5`) then reads the scratch; this only changes the YM image of the driver, never the state used here [disasm].
- On every entry into the 3D view: the YM is silenced once (mixer reg 7 |= $3F, volumes 8-10 = 0: the title music may have left notes on) and the Microwire is set up once per boot (bus error guarded, see §8): master 40, left/right 20 (0 dB), treble/bass 6 (flat), mix = DMA + YM. (Hatari's default state was audible, but I could not see the real STE reset state: treat as `[INFERENCE]` for real hardware.)
- 68020+ (TT/Falcon, `_CPU` cookie >= 20): the instruction cache is cleared after the operand patch (`movec cacr`). The code itself uses only 68000 instructions.

## 3. Voices and priority rule
Per tick, after the original driver ran, for each of its 3 channels (state at `driver+$3D6 = $11388`):
- active = duration `$10+c` != 0 (`$FF` = loop until replaced); effect id `$18+c`; game volume word at `+4+2c` (0..15, the distance-based volume of `$2E8E`); a fresh start = lock counter `$c+c == $32` for exactly one tick (generation counter, age counter in ticks).
- Volume = game volume, times the Amiga envelope for the two effects that have one (17 and 18, "tired" breathing: Amiga envelope 2, a swell, table `ENV2` built by simulating the Amiga envelope code at soundfile `+$ae..$102`). The ST envelopes of the driver are YM imitations (e.g. the rotor's 15/0 chop) and are not used.
- Candidate key = priority class (the game's `$AF38` table: death 1, ping/beep 2, explosions 3, engines/rotor 4, missiles 5, bullets 6) << 8 | (15 - volume) << 4 | min(age, 15). Lower is better.
- **Rule**: voice 1 = the best *one-shot* (non-`$FF` duration), or if there is none the best candidate; voice 2 = the best of the remaining candidates. So an engine/rotor loop keeps one voice while the highest-priority, loudest, newest one-shot (explosion, shot, ping) gets the other; with no one-shot the two best loops play. A bullet (class 6) is therefore never starved by two engines.
- A voice keeps its channel and phase while its channel is still chosen and has not restarted (generation unchanged). A one-shot that was not chosen when it started and is promoted later starts at `age * 125 * inc` samples into the sample. A one-shot that has ended is not restarted until its channel starts a new effect. Volume 0 (an engine at speed 0 fades out one step per frame) removes the candidate.

## 4. Engine pitch (the Amiga mapping, copied)
- The Amiga main code at `$2DEA` (analogue of the ST `$2EB6`): `period = effect_period - 4 * speed` with `speed = $3E(object)` (word), written to the channel's period each frame; speed 0 = volume 0 (the ST fades instead). `effect_period` is the word in the effect record (soundfile `+$430`, e.g. 448 for effect 10, 503 for 11, 895 for 7) [disasm of Amiga `$2DEA` and `$B12A`].
- ST side: the channel record `$1de(a5)+8c` has a flag byte (`$FF` = engine object) and the object offset at `+6`; the object is `$262(a5)+offset` and its `$3E` word is the speed. Pitch is applied only to flagged channels, as on the Amiga (the same set of objects: bit 19 of the object flags). Unchanged speed skips the recomputation.
- `inc16.16 = (K4 / period) << 2`, `K4 = 9285653` (`PAL_CLOCK * 65536 / 6258.29 / 4`, one `divu.w`), period clamped to 284..2047 (inc < 2.0 = 12.5 kHz at the top, 1.7 kHz at the bottom).
- [obs] Speed values: jeep (effect 10) `$3E` = 0 standing, 9 at full throttle (`1mb_car_stand` + Up; it then stays 9). Pokes of `$AA6` (the player's `$3E`) 1/5/9/20/40 in `snd_test record engine_speeds`: the poll shows `inc` 1.2764/1.3242/1.3755/1.5400/1.9678, and the loop period of the engine sample measured in the Hatari WAV (autocorrelation of the DMA stream) is 4846/4672/4497/4017/3144 samples = inc 1.2765/1.3241/1.3756/1.5400/1.9676. So the playback pitch matches the mapping exactly. With the real jeep the whole range is 1.265 -> 1.376 (+8.7 %), the same small swing as on the Amiga.

## 5. Mixer
- Bank (`tools/snd_build.py`, `$90000`, 124126 B of the 126976 available): 21 effect records (sample address, end index, loop length, Amiga period, flags, base increment), priority class table, `MULV` (game volume x envelope), `ENV2`, 16 volume tables of 256 B (`out = clamp(round(s*k/30), -64, 63)`: half scale per voice, so two voices never overflow 8 bits), the 12 samples at their native rate with 512 pad bytes (loops: the loop again, one-shots: zeros, so no bounds check inside a VBL), and a half-scale copy of the 6 loop samples (= table 15, index-aligned).
- Per output sample: nearest-neighbour phase stepping (`add.w incf,frac / addx.w inci,idx`, 16.16), then `move.b (base,idx)` and a volume-table lookup. A voice at volume 15 whose sample has a half-scale copy (the player's own engine, the rotor) uses the copy directly: no lookup, bit-identical output. Five unrolled (x8) routines: `mix1t/mix1d/mix2tt/mix2dt/mix2dd`, `mixz` (zero fill).
- Ring: 1024 B looped DMA frame (`$8F800`), write cursor kept `TARGET = 192` samples (30.7 ms) ahead of the DMA counter (`$FF8909/0B/0D`, read twice until stable), groups of 8, one split at the ring end. Underrun (DMA passed the cursor, > 768 behind) = resync 16 samples ahead (observed 0 times in normal runs). The phase advances only with the samples written, so the audio never depends on the VBL jitter. After 12 silent ticks the DMA is stopped (no zero-fill cost when nothing plays).
- DMA setup: start/end registers, `$FF8921 = $80` (mono, 6258 Hz), `$FF8901 = 3` (play + repeat).
- **Falcon (FLAGS bit3): 12517 Hz, every sample twice.** `snd_dmastart` writes `$FF8921 = $81` and a second ring instead (`$8FC00..$8FFFF`, 1024 B, `DRING`), because Hatari's Falcon plays nothing at `$80` (ttfalcon.md §8; real hardware [INFERENCE]: not checked, no document found that confirms 6258 Hz in the Falcon's STE-compatible mode). The mixer is untouched except for the ring length: its ring (`$8F800`) is 512 samples on the Falcon (state words `v_rl/v_rm/v_msk/v_thr` at `SV+$F0..$F6`, set once in `snd_init0`: 1024/1023/1016/768 for STE-class, 512/511/504/384), and after each `snd_mix` call `snd_expand` copies the new samples (`v_wr`, `v_run1/v_run2` groups of 8) to the DMA ring, `move.b (a0)+,d0 / move.b d0,(a1)+ / move.b d0,(a1)+`, at byte offset 2*index. DMA ring length stays 1024 B = 512 samples = the same 83 ms, `TARGET` is still 192 samples (30.7 ms, = 384 bytes at 12517 Hz); `snd_dmapos` returns (counter - `DRING`) mod 1024 >> 1; the underrun threshold is 3/4 of the mix ring (384). Pitch and duration are those of the STE (6258 Hz sample stream, each sample held for 2 ticks of 12517 Hz). STE, Mega STE and TT take exactly the old path (mixcheck below: 215 ticks bit-exact on the STE).
- Falcon detection is `FLAGS` bit3, set by core.s `probe` (bit0 and the **real** `_MCH` cookie of TOS's own jar, `$5a0`, high word 3). Hatari's STE and TT do not bus-error on Falcon-only registers (`$ff8930/32` read without a fault on an STE), so a register probe is no use there; the game's own jar (D15R_F5's `_MCH`) says Falcon on a TT too, and the game later overwrites TOS's jar (`$980` holds code in the running game), so the bit is sticky: the floppy stage 2 probes first, while TOS's jar exists, the payload entry probes again and keeps bit3 [obs: Falcon floppy `FLAGS=0b`; TT/STE `03`]. HD build on a Falcon: the probe runs at the START stub before the game's loader, TOS's jar should still be intact [INFERENCE: the Falcon HD build cannot be booted here, ttfalcon.md §3].

## 6. Evidence [obs]
All with Hatari 2.6.1, `--sound 50066` + `hatari-shortcut recsound` (WAV capture; HOME is redirected to `/tmp/hsnd/home` whose config has its own `szYMCaptureFileName`, so concurrent Hatari users do not share `/tmp/hatari.wav`). Effects are injected by writing the driver request byte (`$11388+ch`) and volume word (`$1138C+2ch`) exactly as the game's trigger `$AF0E` does; `--quiet` first turns the game's own triggers off (`$AF0E = rts`) and idles the three channels.
1. **Mixer bit-exact** (`snd_test mixcheck`): breakpoints on the entry and the end of `snd_mix`; for each tick the 1024-byte ring and the voice phases written by the 68000 are compared with a Python model reading the same bank. 4 scenarios x ~80 ticks: 1009 ticks, **0 differences**. Coverage (voices, mode): 1 voice table, 1 voice direct, 2 direct, 2 direct+table, 2 table, including loop wraps and ring-end splits.
2. **Explosion / gunfire** (`work/snd/explosion_gunfire.wav`, snapshot `1mb_foot_stand`, quiet; requests at 1.0 s effect 3 vol 12, 5.0 s effect 6 vol 14, 8.0 s effect 4 vol 10): `snd_test compare` correlates the DMA stream of the capture with the model render of that effect:
   `effect 3: onset +23 ms, |rho| 0.9948`, `effect 6: +38 ms, 0.9914`, `effect 4: +35 ms, 0.9867`. The sound is the Amiga sample (the stream is the ring, sign-inverted and x~92 by Hatari's DMA mixing, constant across runs). The WAV is silent between the effects (DMA stopped).
3. **Engine pitch while driving**: `work/snd/engine_speeds.wav` (poked speeds, §4 numbers) and `work/snd/engine_accel.wav` (`1mb_car_stand`, Up held from 3 s: the engine voice starts when the speed leaves 0 and its increment rises with the speed words, polled in `engine_speeds`).
4. **2-voice overlap** (`work/snd/overlap.wav` rotor effect 13 vol 10 from 1.0 s + effect 3 vol 12 from 3.0 s; `overlap_vol15.wav` both at volume 15 = table-free path): in 0.2 s windows over the overlap the capture correlates with the two-voice model at mean |rho| 0.93 (min 0.82) against 0.48 for the rotor alone and 0.85 for the explosion alone (vol 15 pair: 0.92 / 0.55 / 0.81). The rotor alone before the explosion: 0.97. Alignment slips by one sample every ~4 s in the capture (Hatari's DMA clock is 6258.5 Hz, the analysis splits 50066 Hz by 8); the windowed search absorbs it, it is not a mixer error.
5. **Leaving the 3D view** (poke `$899 = 0`, breakpoint right after the DMA-off instruction): `$FF8901 = 00`, `in3d = 0`; the DMA restarts when the game sets the bit again. In 12 s of walking `$93` bit 7 never cleared (601 ticks, 0 `snd_off3d` calls).
6. **Plain ST is unaffected**: cold boot ST 1.04 1 MB (`FLAGS=6`): payload mode 1, `$FF8901` never touched, the injected explosion plays on the YM (WAV `final_st_1mb.wav`, rms 730). Snapshot run with `FLAGS=2` against the unpatched game, identical injection at an absolute VBL: onset 1.8182 s in both, RMS envelope correlation 0.9989, spectral centroid 5240 / 5230 Hz (the YM noise phase differs by a few cycles, as expected).
7. **Cold boots of the final build** (`huntpatch.py build --only snd_core --samples build/hunter_snd.bin`): STE 1.62 1 MB and 4 MB: `HNPO`, `FLAGS=3`, mode 2, DMA on after an injected explosion, capture correlation 0.99; Mega STE 2.06 4 MB: `HNPO`, mode 2, DMA on; ST 1.04 1 MB: mode 1. TT / Falcon: see §8.

## 7. CPU cost [obs] (Hatari profile `profile cycles`, 8 MHz STE, cycles per VBL = 160256 per 100 %)
Payload = everything in `$8E000..$8EFFF`; the original driver (`$10FB2..`) costs 806 cycles/VBL idle and ~3400 with two active channels, in both the original and the patched game. The game's own triggers are off ($AF0E rts) and loops are injected, so both runs do the same game work.

| scenario | payload cycles/VBL | % of CPU |
|---|---:|---:|
| no effect playing | 304 | 0.2 % |
| 1 sustained voice, volume 15 (table-free) | 6,866 | 4.3 % |
| 1 voice, volume 14 (table) | 8,801 | 5.5 % |
| 2 voices, both volume 15 | 11,879 | 7.4 % |
| 2 voices, table path | 15,734 | 9.8 % |
Of those, `snd_update` (channel scan, ranking, voice parameters, DMA position) is 2.0 k (1 voice) to 2.9 k (2 voices); the mix loops are 5.5 / 8.0 / 12.4 k per 125-sample tick = 44 / 67 / 99 cycles per sample (68000 timing with the ST's 4-cycle bus rounding).
The cost applies only while effects play; the player's own engine at full volume is the table-free case. Worst case (two table voices) was 9.8 % of the CPU.
FPS table (600 VBL, flips of `$FF8203`; frames last whole VBLs): see §7.1.

### 7.1 fps, original vs patched (same injected loops, game triggers off)
Two sustained loops injected (the worst case: an engine and a rotor playing continuously); `orig:2` = the original game with the YM driver playing the same two effects; `p2/15` = both voices volume 15 (table-free path), `p2/14` = table path, `p1/15` = one voice. Frames last whole VBLs, so one extra VBL per frame is a 10-15 % step; cycles are the exact measure.
| snapshot | orig:2 fps (VBL/frame) | p1/15 | p2/15 | p2/14 |
|---|---|---|---|---|
| 1mb_foot_stand | 4.58 (10.9) | 4.17 (12.0) | 4.17 (12.0) | 3.83 (13.0) |
| 1mb_foot_walk (Up) | 7.75 (6.45) | 7.58 (6.59) | 7.25 (6.90) | 7.08 (7.06) |
| 1mb_car_stand | 5.50 (9.09) | 5.50 (9.09) | 5.00 (10.0) | 5.08 (9.84) |
| 1mb_car_drive (Up) | 7.17 (6.98) | 7.17 (6.98) | 6.25 (8.0) | 6.25 (8.0) |
| 1mb_car_turn (Up) | 6.25 (8.0) | 6.25 (8.0) | 5.58 (8.96) | 5.58 (8.96) |
| 1mb_hills_stand | 5.83 (8.57) | 5.58 (8.96) | 5.42 (9.23) | 4.92 (10.17) |
| 4mb_foot_stand | 4.50 (11.1) | 4.17 (12.0) | 4.17 (12.0) | 3.83 (13.0) |
The scene is slower by 0 to 8 % (one voice) and 2 to 13 % (two voices) while those loops play; with nothing playing the patched game costs 0.2 % (no measurable fps change: foot_stand 4.50 / 4.50, walk 8.08 -> 7.83 within the 600-VBL quantisation, car_stand 5.58 / 5.58 in the first run).

## 8. Other machines
- **Hunter itself could not be cold-booted on TT / Falcon here**: `Hunter()` builds an ACSI HDDRIVER image, which a Falcon (IDE only) does not see; the TT run did not reach the game either (`huntpatch.py boot` has no TT/Falcon result, loading.md §3). So there is no game-level result for them.
- **DMA programming on TT (TOS 3.06) and Falcon (TOS 4.04) in Hatari** (`tools/snd_dmatest.s` (`vasmm68k_mot -Ftos`, put it as `AUTO\\*.PRG` on a floppy image), a 1.3 KB AUTO-folder program with the payload's exact register sequence: guarded Microwire writes, start/end, `$FF8921 = $80`, `$FF8901 = 3`, the `movep.l` position read checked to be inside the ring): a 391 Hz tone for 4.1 s on both (STE control: the same), position read plausible, no crash. The Microwire writes are guarded (`snd_microwire` installs a bus error handler like the loader's probe) because the Falcon probably has no Microwire registers `[INFERENCE]`; the test does not distinguish between "answered" and "faulted and caught". The payload on those machines is therefore expected to work; the loader sets `FLAGS` bit0 by its own probe and `_CPU >= 20` triggers the `movec cacr` flush. `[INFERENCE]`: Hunter's own behaviour on them (the game + Gamex there).
- Mega STE 2.06, 4 MB (cold boot of the final build): `HNPO`, `FLAGS=3`, payload mode 2, DMA on after an injected explosion (WAV capture of that run failed: Hatari wrote no readable file; the DMA registers and the position were read back live).
- **Falcon correction**: the "391 Hz tone on the Falcon" above is not reliable (ttfalcon.md §7: Falcon WAVs of that time were a shared capture file); Hatari's Falcon plays nothing at `$FF8921 = $80`. The payload now runs the Falcon at `$81` with doubled samples, see §5 and ttfalcon.md §8 (Falcon floppy captured: explosion rms 506-525, engine loop period 0.7813 s = STE).
- Test-tool note: `snd_test.py` now uses `/tmp/hsnd/home_<pid>` and `/tmp/hsnd/cap_<pid>.wav` (per process, removed at exit); §6's `/tmp/hsnd/home` is the old path.

## 9. Known limits, risks, open points
- **Real STE hardware is untested**: Hatari is the only evidence. Microwire defaults, the DMA position register read (`movep.l` of `$FF8909..` twice until stable) and the 6258 Hz frame register behaviour are what Hatari does. [INFERENCE] The loader's probe (`FLAGS`) already read-tests `$FF8905`.
- 8-bit resolution: each voice has half scale (6-7 bit) so two voices fit; distant sounds (volume 3 = 1/5 scale) are coarse. The Amiga had 6-bit volume over 8-bit samples.
- Native sample rates 1.7-9.4 kHz are stepped to 6258 Hz without filtering (zero-order hold, like Paula), so rates above 6258 Hz alias (explosions at 8.4 kHz, bullets); the user picked 6258 Hz after listening to `ste_preview.py` renders.
- Latency request -> sound is 23-38 ms (up to one 20 ms tick plus the 30.7 ms ring lead).
- IKBD: the tick runs with IPL 7 like the original; it is up to ~2 ms longer with two voices. In 500 ticks with two voices mixing and the stick held the ACIA status at the end of the tick was always `$02` (no pending byte, no overrun); the first joystick answer byte arrives ~3 ms after the command [INFERENCE from the IKBD baud rate: 7812 baud = 1.28 ms per byte].
- Sample bank is 124126 B of the 126976 B budget `$90000..$AEFFF` (2850 B spare); `$B8200..$BFFFF` is not used.
- `inc < 2.0` (max pitch 12.5 kHz) and 512 B pads bound one tick at 31 groups x 8 = 248 samples x 2.0 = 496 source bytes.
- The stuck engine: the Amiga silences an engine at speed 0 immediately, the ST driver lets the volume fade one step per frame; this port keeps the ST behaviour (volume word from the game).
- Effects not heard live (ids 0, 8, 9, 12, 16 per sound.md) share the code paths of the tested ones; their sample/rate come from the same table.
- Hatari's DMA path inverts the sign and scales by ~92; irrelevant for the game, but any WAV-based comparison has to allow it.

## 10. Commands
```
python3 games/in_progress/hunter/tools/snd_build.py                      # build/hunter_snd.bin from alt/amiga/*.adf
cd games/in_progress/hunter && python3 tools/huntpatch.py live --only snd_core --samples build/hunter_snd.bin --out build/live/snd
python3 tools/huntpatch.py build --only snd_core --samples build/hunter_snd.bin --out build/snd_game    # cold-boot build
python3 games/in_progress/hunter/tools/snd_test.py mixcheck --inject 13:2:15@0 3:1:12@0.6
python3 games/in_progress/hunter/tools/snd_test.py record NAME --snap 1mb_foot_stand --quiet --inject 3:1:12@1.0 --secs 6
python3 games/in_progress/hunter/tools/snd_test.py compare work/snd/NAME.wav 3,12,1.0,2.5          # EFFECT,VOLUME,T_REQUEST,SECONDS
python3 games/in_progress/hunter/tools/snd_test.py overlap work/snd/overlap.wav 13,10,1.0,3,12,3.0,6.0
python3 games/in_progress/hunter/tools/snd_test.py cost --snap 1mb_foot_stand --cfg orig:2 patch:2:15 --vbls 300 --fps-vbls 600
python3 games/in_progress/hunter/tools/snd_test.py coldboot --machine ste --tos 1.62 --mem 1024 --record NAME
```
