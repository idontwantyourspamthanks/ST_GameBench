# Milestone 3 gate results: TEST DRIVE FROM THE CURSOR + floppy title hint (MSREditor5, 2026-11-22)

Builds: `msrpatch.py build --out /tmp/msred5/hd` (HD) / `build --floppy --out /tmp/msred5/fl`; v1.1 references: `/tmp/msred/v11/MOONSHR` (HD), `dist/MoonshineRacers_floppy_v1.1.zip` unzipped to `/tmp/msred5/v11fl`. Hatari 2.6.1, private HOME, one Hatari at a time, cold boots, every key a real IKBD scancode (`hatari-event keypress`), joystick = debugger writes of `$6105` as in the earlier gates. Env `env5.sh`, raw logs `logs5/*.txt`, screenshots `logs5/shots/` (git-ignored PNGs). Design: `work/notes/editor_design.md` 13 (written before the code) and 14 (built).
`msrpatch.py verify`: ALL OK (HD and floppy default sets, both flavours assemble, no overlap).

## Main gate `td3.py` (HD STE TOS 1.62, 2 MB; campaign `c3.trk`; COPY OF TRACK 04; the final build, `logs5/td3_ste.txt` = full run before the last cp_title-only change, `td3_ste_final.txt` = quick run on the final build)

Edits made through the UI before the drives: 3 + 4 + 2 bend keys (`.` / `,`) at segments 20 / 60 / 120, `I` (insert a copy) at segment 100: 314 segments / 380 objects, vMod set. BAR at unit 19199.

| drive | cursor unit (segment) | race start: distance `$5ff8` | rings (curve / left / right / hill, 1024 entries each) vs the Python expansion of the block read back from ENCBUF | object slots vs objects of the window | ended by | back in the editor |
|---|---|---|---|---|---|---|
| A start | 0 (0) | 0 | 0 / 0 / 0 / 0 mismatches | 25 == 25 | **Esc** after 5 s of driving ($5ff8 478 -> returned at 496); 1.6 s from key to editor | same cursor, 314 seg / 380 obj identical, keys work |
| B middle | 9054 (128) | 9054 | 0 / 0 / 0 / 0 (heads `$1bba` 1724, `$13ae` 862, `$23c6` 862) | 15 == 15 (window 9054..10077) | **F10** (a quick tap; see the finding below), 1.6 s | same |
| C near the BAR | 17789 (275) | 17789 | 0 / 0 / 0 / 0 | 14 == 14 | **the BAR** (joystick up, 23.7 s: `$5ff8` 19190, tdvbl `why` = 1, cut 1.5 s after the stop) | same |
| D 700 before the BAR | 18553 (290) | 18553 | 0 / 0 / 0 / 0 | 27 == 27 | **time-out** (standing: the bar `$10ce` started at 0xf6716a against the formula's 0xeab780 + 8 s of passes; `why` = 2), 8.1 s | same |

Every row also checks: the race stands without further input (`td_ff` ran, V_TD set, `$23c0` in ENCBUF `$1b0000..`, `$102c` = base level 3); `$1028` and V_TD cleared and `$102c` as before after the return; IKBD vector = the editor's hook again and VBL vector = `$d11e`; RIGHT moves the cursor after the return and LEFT puts it back. The time bar start was within the tolerance of the formula `$ff0000 - (2 x R/10 + 100) x $10d2` (R = BAR - 500 - N, clamped at 0 = the stock bar: A and B are clamped; C and D are not). 69 checks PASS, 0 FAIL (`logs5/td3_ste.txt`).
Then (same boot): Esc -> track list (the kept edited track is the 4th) -> **PLAY THIS TRACK of campaign track 1 (normal race)**: race of campaign position 0, V_TD = 0, stream pointer in the campaign store (`$1100d4`), `$5ff8` starts at 0, driven to the BAR (`$1024 = $ff`, full end sequence) -> **shop with a real EXIT click** -> the next campaign race starts (position 1, base level 3, `$5ff8` 0, V_TD 0). PASS.
Screenshots: `td3_ste_{A_start,B_middle,C_nearbar,D_timeout}_{cursor,race_standing,back}.png`, `B_middle_race_driving`, `10_normal_play`, `11_race_after_shop`.

Quick drives (A start / Esc, B middle / F10; same edits, same ring / object / time-bar / return checks): **Mega STE TOS 2.06, 2 MB: ALL CHECKS PASS (38)** (`td3_mste.txt`); **ST TOS 1.04, 2 MB: ALL CHECKS PASS (38)** (`td3_st.txt`); STE again on the final build (`td3_ste_final.txt`, 38 PASS). Bus/Address error lines in the Hatari log: STE 3, Mega STE 0, ST 5 (the same counts the stock flows print, as in RESULTS_m2).

## Findings and fixes during the gate
* First run: `$5ff8` was 65535 after `td_ff` and the bar garbage: the game's updaters use every data register (d7 is the `dbeq` counter of `$fe50`); the counters now live in memory. Evidence `probe1.txt` (the race itself, the time-out return and `V_TD` handling worked on the first try: `$102c` 0x8003 -> restored, editor `state` 1, "BACK FROM THE TEST DRIVE").
* A quick tap of the real F10 did not end the race (td3 run 2: back only after 150 s, when the bar ran out and the time-out ended it): the race loop polls the F10 hold byte `$6042` once per pass (10 / s) and the BREAK code clears it again at once. `tdkb` now keeps a flag and re-asserts `$6042` after every IKBD byte (Esc and F10). Fixed; the rerun passes (1.6 s).

## Step 2: floppy build, F10 hint on the title (`flhint.py`, `flshot.py`; `msrpatch.py build --floppy`)
* `cp_flhint` (floppy only, `; gate: ram2mb`) hooks `$7446` (loop body of the title's face / text loop) and draws `F10 = CAMPAIGNS` (the existing `t_whint` through the existing text call) on both screens at the start of every message. First try (one draw at `$742e`) was gone after the first message because the loop clears both screens from line 64 down between messages (`jsr $d8ca`): fixed and re-shot.
* **Floppy STE 2 MB**: IB+4 = 0xff, `$7446` = `4eb9000b9f12`; the hint is on screen in all four shots (messages 1, 2, 3, 4 at +150 / +500 / +900 / +1300 VBL; `flhint_2m_title_*.png`), F10 -> campaign menu (`flhint_2m_after_f10.png`: LOAD CAMPAIGN FROM DRIVE A / B, no editor item). Byte check of the two game screens at the end of message 3 (`flshot.py --nth 3`, breakpoint `pc = $74c8 :3` armed at power-on, no input): text row 23 non-zero on both screens at 2 MB.
* **Floppy STE 1 MB**: `$7446` = `21d210e8205a` (stock), IB+4 = 0. The two game screens ($70000 / $78000, 32,000 B each) at the end of message 3 and message 5 are **byte-identical to the v1.1 floppy build's** (0 differing bytes in lines 0-199; row 23 empty; `fls_1m_new_n3/n5` vs `fls_1m_v11_n3/n5`; the dumped 768-byte tails beyond the screen differ, which is why the md5 of the raw dump files differ). Timed screenshots (`flhint_1m_*`) are NOT comparable pixel for pixel between two runs (typing progress differs by a few VBL): they were only used to look.
* Not run: floppy Mega STE / ST titles, the floppy hint at 4 MB.

## 1 MB absence on the HD build (`abs1m.py`, STE 1 MB, final build; `abs1m_ste.txt`): ALL CHECKS PASS
RUNME.TOS (73,107 B) differs from v1.1 in 4,148 bytes, all inside cp_title's blob, cp_fetch's and cp_td's blobs (`$B8070`, `$B8260`: never executed at 1 MB) and the trampoline's own tables; HAGA / MS1 / MS2 / MSR_S1.FIC identical; marker MSPO, IB+4 = 0; the nine campaign sites incl. `$7926` hold the stock bytes; F10 at the title = a key; a race runs; no instruction of cp_title's blob executed; no GEMDOS call names MSEDIT.OVL (111 trace lines). (The abs1m script was extended for cp_fetch / cp_td and the new jump-table anchor `$B9F18`.)

## Welcome-screen hint after the cp_title refactor (`welcome.py --full`, HD STE 2 MB, final build; `w5_full.txt`): ALL CHECKS PASS
V_WELC set, hint on the screen, F10 -> menu, Esc -> welcome again (V_WELC 0xff again), F10 -> LOAD CAMPAIGN -> track 2 -> a race of campaign position 1. (e3 now calls the shared `hint` routine that the floppy title also uses.)

## Not run / limits
* 4 MB cells, Mega ST, TT / Falcon, real hardware. The floppy build has no editor, so no test drive there.
* Crash ending (three crashes end a race: `$1026`, `$116e2`) was not provoked; it uses the same `rts` of `$76f4` ([INFERENCE]).
* The time bar start is checked against the formula; whether 2 x full-speed time + 10 s is the right feel for a human player was not judged.
* The title tune: the editor's music is the title's (silent after `$8bb6`); not listened to.
* Hatari-only; the HAGA window for the race setup reads of the test drive (6 `$d6fa` calls) behaved like a normal race load in every run.
