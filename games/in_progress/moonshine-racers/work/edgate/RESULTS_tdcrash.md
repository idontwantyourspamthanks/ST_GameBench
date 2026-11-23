# Test-drive crash investigation (MSRDriveCrash, 2026-11-23): NOT REPRODUCED

User report (preview 2, Hatari STE): PLAIN STRAIGHT -> H -> RISE BIG -> P: `Address Error reading at address $2475, PC=$edc4`, then `Address Error writing at address $fffffc6f, PC=$e09598` (TOS exception loop), bus errors at `$48f00000`.
Result in one line: the crash did not happen in ~25 drives of the same flow on STE 2 MB (incl. the user's 1 MB boot -> Hatari memory 2 MB -> reset sequence), nothing in td_ff / the ring / object / time bar state was out of range, and no source change was made.

## Setup
Build `/tmp/msrcrash/hd` from the tree: RUNME.TOS md5 `7ff3733dfaa10a8faf1f29aabdfe0694`, FILES/MSEDIT.OVL md5 `3d52ea1c874549406fbc5dda4a837290` = the preview 2 files (the lead's md5s). `tools/play.sh` has no `--ram` default other than 1024 (`--ram KiB` is the option) and builds `msrpatch.py build` of the tree into `build/play-hd-patched`: the same build.
Harness: `envcrash.sh` (private HOME `/tmp/msrcrash_home`, work dir `/tmp/msrcrash`, raw logs `/tmp/msrcrash/logs/*.txt`; one Hatari at a time); scripts (all in this directory): `crash1.py` (plain straight -> H list item -> cursor -> P -> drive; options `--level --hill --seg --obj --drive --rand --from1m --camp --pdelay --dump`), `crash2.py` (1 MB -> 2 MB reset exploration), `crash3.py` (repeated drives from alternating cursor units). The harness adds `--alert-level fatal` for the memory switch (without it `hatari-option --memsize` opens a blocking SDL dialog).

## What `$edc4` is
`$edc2` is `eor.w d1,(a1,d0.w)` in the game's wheel-animation XOR routine `$ed74..$edca` (stock RAM dump `work/dumps/ram_race_up.bin` and the patched RAM of a test drive `/tmp/msrcrash/ram_race.bin` agree; the patched build enters it through tb_carph's `jmp $BFC00` at `$ed90` and returns to `$ed98`). It runs for the PLAYER CAR slot `$2c68` (callers `$11296` / `$11342`: `a2 = $2c68`, only when the car moves: `$130c != 0`, once per change of the flag `$122a`, cached per world tier in `$1227..$1229`): `a0 = $34(a2) + (bitmap index) x 14` (the car bank, tier 0 = `$2156a`), `a1 = (a0)` = the car bitmap, `a3 = (a4)` = the XOR list, `d0` = offset words from the list. `$2475` odd and in the hill ring (`$23c8..$27c7`) means a1 (a bank record) or the list was garbage: the car bank / its records were not the loaded graphics, or a1 / a3 came from corrupted low memory. It is NOT an index computed from the track (the indices are 0..24 fixed loops `$1130c`, `$11362`).

## Reproduction attempts (STE, TOS 1.62, HD build, sound on, cold boots; every drive checked for `Address Error` / `Bus Error` other than the harmless `$ff8e21` probes; Hatari prints 3 of those per boot, 4 after the memory switch)
| cell | what | result |
|---|---|---|
| `crash_ste2m_L0` | plain straight, scenery level 0 (BAR 19958 as in the user's report; level 3 gives 19199), H > RISE BIG (segments `[0,16384,accel +1]`, `[16384,16384,accel -1]`), P from unit 0, real time, UP held 30 s | race runs to `$5ff8` 2928, no error |
| `crash_ste2m_L0b` | same, fast-forward 150 s | race ends by the time bar at `$5ff8` 14603 (`$1024` = $ff, the editor's return), no error |
| `crash_A` / `crash_B` / `crash_C` / `crash_D` | A: no hill, from 0; B: hill, from segment 1 (unit 16384, 17 fast-forward chunks); C: hill, from the BAR object (unit 19958); D: no hill, from the BAR object | A: ends at 15696 (time bar); B: reaches 19915 and ends; C and D: the race stands at `$5ff8` 19958 with `$1024` = $ff at once (the BAR is at distance 0: finished), no error |
| `crash_R1` `R2` `R3` | random joystick (UP / LEFT / RIGHT / FIRE / DOWN mixes every 0.25 s), hill / no hill / hill, fast-forward | races end at `$5ff8` 8394 / 8068 / 6812 (time bar), no error |
| `crash_F1` | the user's sequence: boot at 1 MB (`$42e` = $100000, title up), `hatari-option --memsize 2048` (Hatari cold-resets and the HD autostart runs the game again), title, editor, straight, H > RISE BIG, P, drive 60 s | `$42e` = $200000, race runs and ends at 15696, no error (4 benign bus errors) |
| `crash_camp` | campaign c3.trk loaded, straight, H > RISE BIG, P, drive | no error |
| `crash3_a` | 12 drives in one boot on the hill track from unit 0 / 16384 alternately, random drive time, Esc each time | 12 x back in the editor, no error |
| `td3_straight_*` (below) | the regression cells: plain straight / hill from 0 / hill from 16384 / three splits and from 19456 (502 units before the BAR, driven to the finish) | ALL CHECKS PASS (STE) |

Facts established along the way:
* td_ff itself is exact on these tracks: from unit 16384 the four rings equal the Python expansion of ENCBUF entry for entry (curve 0, left 0, right 0, hill 0 mismatches, hill ring = 127 = the clamp), object slots match (0 at 16384; the BAR at distance 502, lateral -48 from 19456), the time bar start matches the formula (clamped at 0 from unit 0).
* A hill with accel +1 over 16384 units does not overflow the game's 32-bit integrator (`$1003c`: d3 = 134,225,920 at the apex, the byte clamps at 127); a count word of 16384 / 32768 in a ring stream is only ever `subq.w #1` / `dbeq`'d (`$ff76`, `$1003c`: no sign test on the count; `tst.w` only for the stream terminator).
* The time bar of the test drive on this track (BAR - 500 - N large) is the stock bar: it runs from `$10ce` = 0 to `$ff0000` at `$10d2` = 10136 per pass, i.e. 1648 passes = 165 s: a plain straight (BAR 19958 = 1996 passes at 10 units per pass) CANNOT be driven to the BAR in the stock time at 10 units per pass; the race ends by TIME-OUT (`$1226` = 5), which `tdvbl` turns into the editor's return. (Consequence for the user's feel: a plain straight times out at about unit 15800 at full speed.)
* `$ef2e` (per-race set-up of the stock campaign loop before `jsr $76f4`: 22 records at `$1b076 + 33 x 14`) and `$7214..$721c` (clears `$1227..$1229`, the car wheel-state caches) are NOT executed by `c_td` (it calls `$76f4` directly). Not shown to matter in any run (all td3 and crash cells pass), but they are the only per-race game state a test drive skips: if the user's crash has a cause in the game state, this is the first place to look.

## Not covered (why the report could not be closed)
* The exact key / timing sequence of the user (real keyboard, real time, other edits before P) is unknown; `crash1.py --pdelay` (P 0.05 s / 0.3 s after the H list's Enter, before the preview / commit work is idle): `crash_pd0.05`, `crash_pd0.3`: race runs (`$5ff8` 15668 / 15843), no error.
* Real hardware, other Hatari settings of the user's own configuration file (not read: private HOME rule).

## Regression cells added (td3.py `--straight`, chain8.sh cells `tdstr` / `tdstrm` / `tdstrs`)
Plain straight (scenery level 0, no campaign): from 0 (one 32768-unit segment) -> H > RISE BIG -> from 0 and from 16384 (fast-forward through 17 chunks) -> segment 1 cut up with S (starts 0, 16384, 18432, 19456, 20480) -> from 19456 (502 units before the BAR) to the finish; every drive does the existing ring / object / time-bar / return checks and the Hatari log is checked for Address / Bus Errors. `td_wait_race` now also waits for `$5ff8` == the cursor unit (td_ff increments `tdhit` at its START, so the old condition could be met while the fast-forward was still running).

## Gate lines (final td3.py; build /tmp/msrcrash/hd; raw logs `/tmp/msrcrash/logs/td3*.txt`)
* `td3.py --straight --nonormal` STE 2 MB: `RESULT td3_straight_ste2m: ALL CHECKS PASS`; Mega STE 2 MB: `RESULT td3_straight_mste2m: ALL CHECKS PASS`; ST 2 MB: `RESULT td3_straight_st2m: ALL CHECKS PASS` (on the ST the Hatari log has the benign STE-register bus errors `$ff8924` / `$ff8a28`, ignored by the filter: only Address Errors and bus errors below `$ff8000` count).
* `td3.py --quick --nonormal` (the stock-copy cells with the changed `td_wait_race` / `BASE` check) STE 2 MB: `RESULT td3q_ste2m: ALL CHECKS PASS`.
* Not re-run: the full td3, the Mega STE / ST quick stock cells and the quick edit gate (no overlay / patch source changed; td3.py's stock path changed only by the `td_wait_race` unit condition and `BASE`).
