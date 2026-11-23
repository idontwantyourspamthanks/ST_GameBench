# HANDOVER 3: Powermonger WW1 Edition — state, and the one open problem

Written 2026-11-23. `HANDOVER.md` and `HANDOVER2.md` hold the history; this file is the
current state and the work to be picked up. Read this first.

---

## 1. One-line summary

The tick, the protection removal, the keyboard shortcuts **and tooltips** are **done and
gated**; the tick, protection and keys are confirmed on the user's real Mega STE. Only
performance is untouched.

Tooltips were unblocked by Grok, who identified the font (runtime `$8406`) and the composer
(runtime `$82c8`) — the latter being the routine this project's own profile note called the
"terrain pattern combine", which is why three earlier searches dismissed it. See §5.3.

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
| tooltips | `tools/tooltipgate.py` | **PASS** — 6/6 icons, correct text, nothing shown off-panel |
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

## 5. Tooltips (done) — and what was hard about them

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

### 5.3 Tooltips — DONE

`work/ttproto/tooltip.s`, patch set `tooltip`, payload at `$72C00`, site runtime `$13e0a`.

**The two facts that mattered, both wrong in my earlier notes:**

| | wrong | right |
|---|---|---|
| the font | `$8976` (1990 address) or `$F8000` | **runtime `$8406`** (text `$8516`) |
| the composer | a separate text routine | **runtime `$82c8`** — the *same* routine as the pattern blit |

`$82c8` paints a 16-pixel (4 glyph) × 6-row strip per call, 48 bytes per group of four
characters, phases from the 8 bytes before the font (text `$850e` = `04 08 0c 00 04 08 0c 00`).
Patterns and glyphs are the same 4-plane cell format, which is exactly why `frameloop.md` §6a
calling it the "terrain pattern combine" sent me away from it. **My own write-watchpoints kept
stopping inside `$82c8..$83f0` and I dismissed them three times as terrain.** That was the
expensive mistake of this port.

How the patch works: the site is the map pass's 32K window copy, so the hook runs that copy
first (back buffer = clean frame) and then paints the hover line into the same buffer. The
next pass's copy erases it — no cleanup code, the 1990 `pm_tooltip` trick unchanged.

The hit test is an exact port of the game's perspective-grid test (tables `$13bde`, `$13c58`,
action table `$1a89a`), because the cells are quadrilaterals and boxes overlap on 24 pairs.
`tools/pwwgrid.py` is the reference; the 68k port matched it on 5200 points, and the assembled
routine was then verified in the emulator.

**Gate**: `tools/tooltipgate.py` — hovers six icons, compares the composed line against
`pwwgrid.NAMES`, requires the top bar to change, and checks nothing shows with the pointer off
the panel. **PASS 6/6.** The release gate still passes with the patch in (world state
untouched).

Traps that cost time here are listed in `input.md` §7.4 — notably that `$2edb2/$2edb4` are
rewritten by the IKBD handler every VBL (so pokes to them last under a frame; use `goto_st`),
and that `movem.l d2-d7` around a routine returning in `d2` wipes the result.

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

`$F8000` is the screen. `$8976` in this build is not the font. Byte column is `x/2`. The
composer is the same routine as 1990 `$8838`, at `$82c8`, and it loads the font from `$8406`.

**Next:** port `pm_tooltip.s` with `FONT equ $8406`, hooked on the `jsr $13a94` at `$13e0a`.
Do not invent a font.
