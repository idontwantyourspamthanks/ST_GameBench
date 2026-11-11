from pathlib import Path
R = Path('/home/ryan/Code/AtariST/midwinter2/work/p7_skip')
note = Path('/home/ryan/Code/AtariST/midwinter2/work/notes/p7_static_skip.md')
def ev(n): return (R / 'evidence' / n).read_text().rstrip()
FENCE = chr(96) * 3
cost = ("| cy/frame (20 frames, same frames in every run, `work/p7_skip/cyc.py`, `profile` between the 10th and 30th flip) | unpatched | p4 + p7 default set | + p7_skip |\n"
"|---|---:|---:|---:|\n"
"| `1mb_ingame_foot` (standing) | 1,898,425 | 1,598,307 | **287,897** (-82.0 % vs p4+p7, -84.8 % vs unpatched) |\n"
"| `1mb_ingame_walking` | - | 1,194,282 | 1,196,783 (+2,501 = +0.21 %) |\n\n"
"Raw (`evidence/cyc_stand.txt`, `evidence/cyc_walk.txt`):\n" + FENCE + "\n" + ev('cyc_stand.txt') + "\n" + ev('cyc_walk.txt') + "\n" + FENCE + "\n"
"The hook on a skipped frame costs 13,768 cy (profile of the hook addresses, 20 frames): stage and scalar compare 1,822, `OBJPASS` (30 units + 30 effects, nothing active) 4,332, `MKCMP` (56 markers x 4 longs) 7,266.\n"
"On a moving frame it is stage + first-long mismatch + copy of the 26 scalar longs: +2,501 cy per walking frame, no object work (the object parts are only recorded once the scalars have settled).\n"
"What is left of a standing frame (287,897): the pre-render logic block (126 k, `render_audit.md`), the HUD gauge/radar/sprite draw `$19f54` (about 144 k, item 5(b) of the plan), flip, interrupts. Profile pages of the skipped frame:\n"
"`$1b000` 70 k (radar `$1b6f4/$1b966`, `$1ba24` probes), `$2b000` 46 k, `$34000` 34 k, `$29000` 28 k, `$36000` 22 k, the hook 13.8 k. Cold-boot frame rates: section 7 (d).")
gaps = """1. **Constants are assumed, not proven.** The bytes the renderer reads and nothing outside it wrote in 35 traced iterations (terrain heights `$40040-`, object models `$3ac36-$3be3d`, sin table `$44a4-$48a4`,
   `$51ce`, `$5266`, `$55876`, `$57054`, `$17a68`, `$18c48-$18d8b`, the cockpit list) are treated as constant. A writer that never ran in my scenes (terrain damage, a mission script editing models) would be missed.
   The cockpit list is covered by the 3D-entry invalidation, the rest is not.
2. **Foot type only.** `$6220 <> 13` (and `$40b6 <> 0`) always renders. Vehicles have more inputs (pitch, other overlay lists, weapon sights) and were not traced; no vehicle snapshot exists.
3. **Not modelled, therefore never skipped**: an active effect record (`$3cee`) or a unit with `$2e = 0` within 16 cells of the player; more than 80 marker records (`MKMAX`); any HUD message timer >= 0.
   Effect and unit-state-0 draws (`$50aa`, `$50a4`) were not traced because I could not create them without a mission event.
4. **Trace coverage**: 35 loop iterations in 7 scenes. Unit field reads outside the traced branch (`+$16`, `+$1e`, `+$20`, only when `$1c6d0` is true) come from the disassembly of `$1c3fc`, not from a run that took
   the branch; `$67be` (shade shift) was 0 in every scene; effects and the cinematic message loops (`$7582 = 0`, `$759c = 0`) were never run, only read in the disassembly.
5. **Window width**: units/effects are looked at inside 16 x `$66e0` units; the game's own test is +-8 cells of `$670a/$670c` (`$20164-$20180`). The margin (rounding of two `divs`, at most 2 cells) is argued, not measured.
6. **Buffers**: the hook takes the buffer index from bit 16 of `$67a6`; true for `$60000/$70000` on 1, 2 and 4 MB (flip `$26e98` writes only `$ff8201/$ff8203`, `frameloop.md` section 5).
7. **Wave pointer**: the animated sea is never skipped (sea views keep the full cost). The wave read sites are the three pc-relative reads of `$1dfba` found by a linear sweep of `$4000-$60000` (`movea.l $1dfba(pc)` at `$1db04`, `$1fd1c`, `$1fd9a`); no
   other reader exists unless it computes the address.
8. **Floppy build** and a plain ST were not run; the sites are resident or overlay addresses identical on floppy (`floppy.md`), the payload range `$B6000-$B7FFF` is zero at staging.
9. HUD (`$19f54`, 144 k) still redraws every presented frame; the clock/radar/messages are untouched (plan 5(b))."""
txt = note.read_text()
txt = txt.replace('COST_PLACEHOLDER', cost).replace('GAPS_PLACEHOLDER', gaps)
note.write_text(txt)
