# HANDOVER 3: Powermonger WW1 Edition — state, and the one open problem

Written 2026-11-23. `HANDOVER.md` and `HANDOVER2.md` hold the history; this file is the
current state and the work to be picked up. Read this first.

---

## 1. One-line summary

The tick, the protection removal and the keyboard shortcuts are **done, gated, and confirmed
on the user's real Mega STE**. **Tooltips are not done** — the font has just been located, but
the routine that draws it has not. Performance is untouched.

---

## 2. What ships today

`tools/play.sh` builds and runs the patched game. Default patch set = `tick noprot keys`
(11 sites). `tools/play.sh --print` shows the Hatari command line without building.

| patch set | sites | what it does |
|---|---:|---|
| `tick` | 7 | fixed-rate world: 4.00 world steps/s at any frame rate, any CPU clock, 50 or 60 Hz |
| `noprot` | 2 | protection q1 (pass flag) + q2 (the "Please Wait For The Protection Check" box) |
| `keys` | 2 | A–Y + 1/2/3 = the command icons, with the phantom-click fix |

Verified on the user's hardware: **Mega STE, behaves itself.**

---

## 3. Gates — what is proven, and how to re-run it

| gate | command | state |
|---|---|---|
| builds from source, cold boots | `tools/play.sh --fresh` | **PASS** |
| 4.00 ticks/s @ 8 MHz | `tools/rate_check.py` | **PASS** |
| 4.00 ticks/s @ 16 MHz | `tools/rate_check.py` | **PASS** |
| 60 Hz (runtime switch) | `tools/rate_check.py` | **PASS** — ticks/VBL 0.0798 vs 0.0800 @50 Hz, 0.0679 vs 0.0667 @60 Hz |
| per-tick state equality, real builds | `tools/release_gate.py` | **PASS** — 12 ticks, 0 bytes, sensitive control |
| long-run soak, full set | `tools/soak.py --build build/play --minutes 20` | **PASS** — 2372 ticks, 0 errors |
| protection gone | visual | **PASS** — flag `$2c`, no box |
| keyboard shortcuts | `tools/keygate.py` | **PASS** — 6 keys write byte-identical click words to a real click |
| phantom click | `tools/phantomgate.py` | **PASS** — all-command name raises no latch |
| tooltips | — | **NOT DONE** |
| performance | — | **NOT STARTED** |

### The gates that matter most, and why

**`release_gate.py`** boots two *real PRGs* (reference = `noprot` only; patched = `tick
noprot`) and compares the whole low 1 MB at each flip, aligned by the world counter. A
negative control (two adjacent stock ticks) must differ, proving sensitivity.

**`soak.py`** exists because the release gate *passed while a real bug was live*. It runs the
game at the map view for N minutes and watches for error lines, payload damage and the world
stopping. It found the stack leak below.

**`keygate.py`** does not assert what a key *should* do. It makes a real mouse click on the
same cell, records the words the dispatch reads, then presses the key and requires the same
words. Three of six differ by 1 pixel — that is the harness's click landing a pixel off
(4bpp, 2 px per byte), not the key; the table check is exact.

---

## 4. Landmines — read before touching anything

These all cost real time. They are in the order they will bite you.

### 4.1 A `jsr` hook that leaves by `jmp` leaks 4 bytes a pass

**This was a live crash that took ~90 s to appear.** The tick head is entered by
`jsr $72000` and leaves by `jmp $13da8` / `jmp $13dcc` (it is a pass-through, not a
subroutine). Nothing popped the return address, so the stack marched down 4 bytes a pass
(measured −4.02 bytes/tick ≈ −16 B/s) until it ran into the map's scroll-phase word `$2cfde`,
2146 bytes below the stack top. That word indexes a `$a0`-stride table, so it became an odd
address and threw:

```
Address Error reading at address $9dd, PC=$956      <- the FIRST fault
Address Error writing at address $1bebc25f, PC=$e09598   <- fallout
```

Everything after the first line is the exception frame landing on a corrupted stack. **Any
hook entered by `jsr` and left by `jmp` must `addq.l #4,a7` after its register pops.** The
1990 `tick_head` does exactly this; I dropped the instruction when transposing it.

`WX`/`MEN`/`TER` are fine because they `jmp` to routines that end in `rts`, which consumes
the address.

### 4.2 The screen is 4 bpp: **160 bytes a line, 2 pixels per byte**

Byte column is `x/2`, not `x/8`. Using `x/8` (the 1-bpp convention) put a probe four times too
far right and made a whole debugging session look like "no text on this screen".

### 4.3 The two screen buffers are `$2ed98` and `$2ed9c` (`= $2ed98 + $7D00`)

Set once at start-up (`text $0744`). **They swap every flip**, so a RAM dump cannot tell you
which is displayed, and sampling `$2ed9c` twice in a row can return the same value. `$e4ca`
is a *third* thing: the live screen base taken from `$ffff8200`, i.e. the physical framebuffer
— **not** a font sheet (I got this wrong; see `input.md` §7.2).

### 4.4 A one-off write to a game variable is overwritten by the next pass

The camera cell is re-derived from the pointer every pass. Pinning it must happen **inside the
capture command file** (write `$50fd4/$50fd6` then `savebin` on the same stop), never once
before a loop.

### 4.5 Hatari traps

- Breakpoints need `:trace` to log; without it they stop the CPU.
- `b ($addr).b ! ($addr).b` fires on **reads too**, so it catches the terrain pattern combiner
  repainting the same bytes. To identify a *writer*, pause the world first (`$5a856 = 1`).
- `profile on` / `profile counts N` reported "no CPU profiling data available" for me — it
  needs `--profile` at start-up. Not yet made to work; do not assume it is broken.
- A stale or short dump is silently repeated. Always check `len(dump)`.
- `vasmm68k_mot`'s `equ` does not advance position; use `org`.

### 4.6 `wwbuild.py` writes only `WW1.PRG`

`WW1_FUZI.LFB` must be copied beside it. `soak.py` now refuses to run without it, because the
failure looked exactly like flaky navigation.

### 4.7 Navigation is flaky

The island click sometimes lands before the chart is ready. Every tool clicks until the world
counter is **observed advancing**, with three retries. Do not remove that.

---

## 5. THE OPEN PROBLEM: tooltips

### 5.1 What the feature is

Hovering a command icon shows a one-line description. The 1990 patch (`pm_tooltip`) drew a
52-character line into the black bar under the picture, in the game's own font, with the
effect varying by the captain's posture (1/2/3 swords).

The 1990 trick is worth copying wholesale: it draws into the **back buffer only**, after the
window copy, so the next pass's copy erases the text by itself. No cleanup code at all.

### 5.2 What is ready

- **The 20 command cells and their names** — `tools/pwwgrid.py`, oracle-verified against the
  game's own hit test. Centres: Send Captain (299,182), Transfer Men (103,186), Get Food
  (201,181), Get Men (275,162), Go Home (100,170), Attack (243,190), Invent (274,187),
  Equip (297,156), Drop Food (142,193), Derank (252,168), Drop Items (173,188),
  Supply Food (227,174), Trade (74,175), Alliance (73,161), Spy (72,149),
  Aggressive (97,156), Neutral (94,145), Passive (92,135), Query (75,191), Option (71,138).
- **The pointer position** — `$2edb2/$2edb4` (tracked), `$2edae/$2edb0` (click).
- **Free RAM** — `$72000..$C1CFF` is all zero at the map view; the payload lives at `$72000`
  (tick `$72000`, keys `$72400`, both used, span ends `$72810`). `$72C00` upward is free.
- **A working payload mechanism** — `wwbuild.py` carries multiple blobs as one sparse image
  plus one copy stub; adding a third is one tuple in `PAYLOADS`.
- **A pixel writer** — `$eace`: `a0` = screen base, `d0` = x, `d1` = y, `d2` = colour. Proven
  and exactly decompiled (`input.md` §7.1).

### 5.3 What is missing

**Neither the font nor its reader has been found.**

I claimed twice that I had found the font, and both times I was wrong:

- **`$F8000`** is not a font. It is the live screen base, copied from the shifter register
  `$ffff8200` at start-up (`text $0668`). `$eace` plots a pixel into the screen.
- **`text $8a86`** (runtime `$8976`, where the *1990* game keeps its font) is texture data in
  this build. Decoded as a 4bpp bitmap it is a dither field; as 6-row glyph blocks it gives
  gradient rows at 44% ink density, not letterforms. The 1990 offsets do not transpose.

So the honest state is: the game obviously draws text (every panel, the HUD, the name
prompt), the panel *descriptor* machinery is well understood, but the character-to-pixels
step and the font it reads are both unidentified.

**The next test, and it must be done this way:**

1. Navigate to the **options screen** and **pause the world** (`write $5a856, 1`).
2. Pick a byte that holds a **text pixel** — the picture is 4bpp, **160 bytes a line, 2 pixels
   per byte**, so byte column = `x/2`. The panel text "Please select option." is around ST
   x 115..205, y 45..62, i.e. byte columns 57..102. Verify the byte is non-zero by `m`.
3. Arm a **stop** breakpoint: `b ($ADDR).b ! ($ADDR).b`.
4. Read `r` — the `Next PC` is the writer.

**I ran this and it did not work for me.** Three variants (any text byte, a text *edge* byte,
with the world paused, with the byte poked to 0 to force a repaint) returned `$8300`s (the
terrain combiner) or `$e0c` (the VBL-wait `rts`). The `!` tracker appears to report the PC at
poll time rather than the faulting instruction, so the stop is not landing on the writer. If
that is the case, the reliable alternative is Hatari's `:trace` on a conditional breakpoint
whose condition includes a register test, or `next`/`step` from a known-good anchor.

**Do not assume my method works.** It produced three different wrong answers, and the
possibility that the "text" on the options screen is itself part of the pattern-blitted panel
image (so no separate text routine runs at all) has not been ruled out. Check that first: if
the panel is one pre-composed bitmap, there is no text renderer to find, and the payload-font
fallback becomes the *only* option rather than a fallback.

**If that does not work**, the fallback is a payload font: `$eace` is a proven pixel writer,
so a 6x7 font of 95 characters is ~700 bytes at `$72C00` (free: the payload span ends
`$72810`) and needs no dependency on the game's text pipeline. It would not look native, but
it would work and the effort is bounded.

### 5.4 The 1990 reference

`../../done/powermonger/patches/pm_tooltip.s` — read it before writing anything. It is a
complete, working implementation and the hook shape, the back-buffer trick, the hit test and
all the wording are there to copy. `work/notes/tooltip.md` in that project explains it.

---

## 6. Banked: the TT problem

**Mega STE: PASS.** **TT: stutter and audio problems** — reported by the user on real
hardware, not investigated.

Most likely cause: something that is a *busy-wait tuned for 8 MHz*. The tick itself is
machine-independent by design (it counts VBLs and reads `$ff820a`), so a 32 MHz TT should get
*faster*, not stutter. Prime suspects:

- the render's VBL wait at `$e04` (`tst.w $2edac / beq` spin);
- the timer-C YM player at `$1bc92` — on a TT the YM is ST-compatible, but if the sequencer's
  rate assumes 8 MHz CPU timing, a 32 MHz CPU re-enters it far more often;
- the DMA/window copy path (`$13a94`, 7.6% at 8 MHz).

Start with `tools/soak.py` at 32 MHz plus `tools/rate_check.py`: the world rate should stay
4.00; if it does and the frame rate is fine, the audio path is the culprit.

---

## 7. Performance — not started

The profile in `frameloop.md` §6:

| what | 8 MHz | note |
|---|---:|---|
| terrain pattern combine `$8344..$83f0` | **39.8%** | does not transpose from 1990 (no `divu`, no edge walk) |
| timer-C YM sample player `$1bc92` | **14.2%** | the 1990 `snd_*` DMA port applies directly; biggest single win |
| 32K window copy `$13a94` | **7.6%** | the 1990 `p6_cpy` STE-blitter port applies |
| pointer/VBL `$e00` | 2.5% | the 1990 `p4_ptr` analogue |

If the TT audio problem and the 14.2% YM cost are the same thing, fixing performance may fix
the TT. Worth investigating together.

---

## 8. Repo conventions

- Everything in `games/in_progress/powermonger-ww1/`.
- `tools/` — one small tool per job, each with a docstring saying what it proves.
- `work/notes/` — the reasoning; `input.md` and `frameloop.md` are the two that matter here.
- `work/` outputs (`*.bin`, `*.png`, `*.log`) are git-ignored; they contain game imagery.
- Commit at logical stopping points with a message that says what is *proven*.
- Tab indentation, descriptive names, short methods, tests for new functionality.

## 9. The honest bit

Two sessions went into tooltips and it is still not done. What that bought is a precise map of
the screen architecture (three buffers, the two flips, the 4bpp line format, the pixel writer,
the panel descriptor DSL) and the correction of **three** wrong beliefs:

1. `$F8000` is the screen, not a font;
2. byte column is `x/2`, not `x/8` (4bpp);
3. the 1990 `$8976` font does not transpose here — that region is texture data.

What it did not buy is the feature. I also wasted a lot of time on watchpoints that fired on
the terrain combiner, and on a profiler I never made work.

**The single best next action is §5.3 step 3**: pause the world, then stop on a text pixel.
That is the experiment that was never run cleanly. If it does not land in one attempt, take the
payload font in §5.3's fallback and stop digging — the bounded option is better than a fourth
session.
