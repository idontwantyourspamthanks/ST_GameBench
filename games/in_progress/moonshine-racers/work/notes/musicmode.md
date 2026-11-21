# Music mode (spare-parts shop "fx / music" toggle): study and fix (MSRMusic)

User report (MiSTer, v1.0.1): selecting "music" in the shop makes all performance gains disappear. Result: **bug in our extra-frame patches** (`mf_sync`/`mg_sync`/`mx_sync` gate on `$1021 == 2`, which is the sound mode, not a race flag). The music itself is fine. Fixed in 5fd79c0 (v1.1). Scripts, logs, diffs: `work/musicmode/` (`mus.py` = the harness, `run*.sh` = the run chains, `logs/*.log` = raw output, `fix_*.diff`, `shop_fx.png`/`shop_music.png`). Raw YM write traces (`*_ym.txt.gz`, about 70 KB each) and profile files stay in `/tmp/msrmus/out/` only.

## 1. Toggle mechanics (stock game, `originals/MOONSHR`, verified by RAM diff across the click and by capstone disassembly of a RAM dump)
- Shop icon at ST pixel (250,30), top right, reads "FX" or "MUSIC". Clicking it flips `$1023` (2 = fx, 1 = music): `$16bd4 move.b $1023,d0 / subq / bne` then `$16bdc move.b #2,$1023` or `$16be4 move.b #1,$1023`. `$16b1c` draws the label from it. RAM diff across the click: `$1023 02 -> 01`, nothing else sound related. The shop itself keeps `$1021 = 2`.
- `$7226 move.b #2,$1023` (game start). `$726c move.b $1023,d0 / cmp.b $1021 / move.b d0,$1021` at the top of every race set-up: **`$1021` is the sound mode of the race (2 fx, 1 music)**, not "race mode". `$7710` sets it to 2 if it is 0.
- Readers of `$1021` in stock code (`m68dis --xref 1021`): `$7932`, `$79c4` (`cmpi #1`: start tunes 1/3/5 on voices 0/1/2 through `jsr $7bba`, at race start and after a pause), `$7994`, `$7a68` (`cmpi #2`: engine pitch `$91f0` from `$10d8` once per pass), `$7bb2` (`cmpi #2`: effect trigger `jsr $8c00`, skipped in music mode), `$72ea`, `$16718`/`$16a98` (save/restore around menus).
- Player: VBL ISR `$d11e` -> `$d486` (IKBD query `$d138`, patched by ta_nomouse) -> `jsr $8bf2` (if `$1020`) -> `$8c38`: one tick per VBL of a 3-voice script sequencer (voice records at `$9344`, stride `$36`; durations in VBL ticks: `subq.w #1,$8(a4)`, note length = script byte x `$e(a6)`; tune table `$c974`), then writes R0-R11 to the YM (`$8e2c..$8e86`, `ta_ymw` site). No Timer A/C, no samples, no dependence on game steps or drawn frames. Fx and music share this one player; only the script ids differ.
- Cost, stock STE 8 MHz profile: player `$8c38` 2.8-3.0 k cycles/VBL (music) vs 3.0-3.2 k (fx), about 2% of a VBL. Passes identical in both modes (below).

## 2. Cause
`mf_sync.s` / `mg_sync.s` / `mx_sync.s` `.r1:  cmpi.b #2,$1021.w / beq.s .r2 / addq.w #1,RSN+10.l / rts` (skip reason 5) was written as "race mode" (same mistake as ta_nomouse v1.0). In music mode `$1021 = 1`, so every tick skips the extras. Steps stay at 10/s (the pacer is separate), frames fall to 10/s: fx 20-28 fps -> music 10 fps.

## 3. Measurements
Method: `mus.py` cold boot (sound on, `--joy1 keys`, 1 MB) -> race 1 -> BAR poke -> shop -> [click FX at (250,30)] -> EXIT -> race 2, `$6105=1` held, 8 s settle. Windows of about 500 VBL (counts) and 300 VBL (YM trace) with `b pc=$X :trace` on `$d11e` (VBL), `$8c38` (tick), `$8cd2` (note fetch), `$d1ca` (flip), `$7b86` (step); `trace psg_write` for the YM window; `msr.prof` 200 VBL. Mega STE runs at 16 MHz natively (the game sets it) and at 60 Hz in Hatari; the 8 MHz Mega STE rows use `set_cpuclock(8)` after the boot.

| config | build / mode | steps/s | flips/s | ticks/s | notes per window | YM writes/VBL |
|---|---|---|---|---|---|---|
| STE 8 MHz 50 Hz | orig fx | 9.28 | 9.28 | 50.00 | 170 | 11.96 |
| | orig music | 9.28 | 9.28 | 50.00 | 256 | 11.96 |
| | v1.0.1 fx | 9.98 | 20.26 | 50.00 | 180 | 2.99 |
| | v1.0.1 music | 9.98 | **10.08** | 50.00 | 259 | 5.02 |
| | fix music | 10.00 | 20.30 | 50.00 | 259 | 5.03 |
| | fix fx | 10.00 | 20.20 | 50.00 | 179 | 2.99 |
| Mega STE 16 MHz 60 Hz | orig fx | 13.65 | 13.65 | 60.00 | 187 | 11.96 |
| | orig music | 13.62 | 13.62 | 60.00 | 269 | 11.92 |
| | v1.0.1 fx | 10.00 | 28.24 | 60.00 | 176 | 2.99 |
| | v1.0.1 music | 10.10 | **9.98** | 60.00 | 272 | 4.74 |
| | fix music | 9.98 | 29.00 | 60.00 | 272 | 4.74 |
| | fix fx | 10.00 | 28.94 | 60.00 | 176 | 2.99 |
| Mega STE 8 MHz 60 Hz | orig fx | 7.06 | 7.06 | 60.00 | 187 | - |
| | orig music | 7.05 | 7.05 | 60.00 | 281 | - |
| | v1.0.1 fx | 9.98 | 11.27 | 60.00 | 187 | - |
| | v1.0.1 music | 9.98 | **9.98** | 60.00 | 281 | - |
| | fix music | 10.00 | 11.29 | 60.00 | 281 | - |

(Not run: Mega STE 8 MHz fix fx.) Key raw lines (`logs/`):
```
v_ste_fx_native_counts:    vbl 501 (50Hz) ticks 501 notes 180 flips 203 passes 100 | steps 9.98 flips 20.26 | extra 134 rsn_delta [0,0,0,0,0,0,0,0,0,0,0]
v_ste_music_native_counts: vbl 501 (50Hz) ticks 501 notes 259 flips 101 passes 100 | steps 9.98 flips 10.08 | extra 0   rsn_delta [0,0,0,0,0,134,0,0,0,0,0]
v_ms_music_native_counts:  vbl 511 (60Hz) ticks 511 notes 272 flips 85 passes 86   | steps 10.10 flips 9.98 | extra 0   rsn_delta [0,0,0,0,0,119,0,0,0,0,0]
f_ste_music_native_counts: vbl 500 (50Hz) ticks 500 notes 259 flips 203 passes 100 | steps 10.00 flips 20.30 | extra 133 rsn_delta all 0
```
Reason-5 skips (134) equal the extras that fx draws (134).

Tempo: ticks = VBL count in every row; voice-A note intervals in VBL: orig `{5: 59}`, v1.0.1 `{5: 57}`, fix `{5: 58}`. Rebuilt YM chip state per VBL (R0-R5, R8-R11; orig vs v1.0.1 and vs fix, shifted to the same song position): 236/236 frames identical (STE), 218 frames identical except the truncated last frame of the stock window (Mega STE), 101/101 at 16 MHz. `ta_ymw` writes fewer registers (about 5/VBL in music, 3 in fx, vs 12) with an identical chip state at every VBL.

Profile, v1.0.1 STE 8 MHz, cycles per VBL (profile total about 121.7 k of 160.4 k):
| item | fx | music |
|---|---|---|
| pacer sleep (`mg_pace` busy wait) | 10.1k | 68.4k |
| render blobs | 69.6k | 33.7k |
| stock code | 22.0k | 12.5k |
| extras code | 9.4k | 0.07k |
| stock YM player | 2.1k | 2.1k |
| `ymw` blob | 0.56k | 0.59k |
Fix music: sleep 10.1k, render 69.6k, extras 9.2k (same as fx). Note: `msrprof.buckets` lumps every address above `$1fc14` into one bucket; the table above is bucketed by blob address range (`$b8180` sleep, `$b8400` extras, `$b3000-b8000` render, ...). The Hatari 2.6.1 profile format has no leading `$`; `mus.py` patches `msrprof.LINE` accordingly (msrprof.py itself fails on the current output).

## 4. Verdict
Not (a), not (c): music mode costs about 2% like fx, tempo equals the original per VBL (the player is VBL driven; our pacer, extras and ta_ymw do not change it). It is (b): the `$1021 == 2` gate disables the extras. No slow-music cause found; [INFERENCE] the "slow" feeling is the 10 fps picture.

## 5. Fix (commit 5fd79c0)
`.r1: tst.b $1028.w / bne.s .r2` in `mg_sync.s` (default), `mf_sync.s`, `mx_sync.s` (`fix_mg_sync.diff`, `fix_mf_mx.diff`): the stock race flag `$1028` (set `$72c0`, cleared `$72d0` around the race call), as ta_nomouse v1.0.1 uses. Prototype numbers are the "fix" rows above. mf/mx variants assemble (`build --only mt_clock mt_pre mf_sync mf_pre hd_stage`, same for mx) but were not run in Hatari.

## 6. Untested / notes
- No real hardware; MiSTer not reproduced. 50 Hz Mega STE not run (Mega STE here is 60 Hz). Plain ST, 4 MB and floppy builds not run (floppy uses the same patch).
- Race 2 only, joystick held, no steering; one race per config; the YM traces are 300-VBL windows.
- A 60 Hz display runs the music 1.2x faster than 50 Hz in the stock game and in every build (tick per VBL).
- Existing, unrelated to music: at 60 Hz stock steps/s exceed 10 (13.6 at 16 MHz), v1.0.1 holds 10.
- Profiles in the patched builds include the pacer's busy-wait sleep as "work" unless bucketed by blob range.
