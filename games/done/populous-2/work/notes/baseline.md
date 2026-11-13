# Populous 2: boot, baseline, world speed, pacing

Second pass, 2026-11-11. 2 MB STE, TOS 1.62, Hatari 2.6.1, PP's HAGA build, no patches. **The first draft never reached the game**: its "map with the query panel open" was the title credits (`work/shots/skip1.png`), so its loop, profile, tooltip strip and "no keypress arrives" claims are void. Dumps: `work/dumps/game_start.bin`, `busy1.bin` (2 MB each). Snapshots: `work/snapshots/game_start.sav`, `busy1.sav`.

## Path to the game (shots `work/shots/c00.png`-`c55.png`)

1. PP's hardware screen: hold Space (a one-VBL tap is not seen; the intro compares `$fffc02` with `$39` once per VBL, and the ACIA keeps the last byte until the release arrives).
2. Cover picture, Bullfrog logo scroller, credits: hold Space once for each.
3. Main menu: CREATE YOUR DEITY / CONQUEST GAME / CUSTOM GAME / LOAD GAME. The first click on CONQUEST opens the deity screen: click the name field, type, Return, PROCEED. Buttons react on their text row only.
4. CONQUEST again: the battle sheet ("BATTLE AT DOEGAC ... WITH THESE EFFECTS: (CLICK FOR HELP)"), PROCEED (ST (60,195)).
5. The manual question is still asked ("HOW MANY STATUES HAVE BEEN BUILT IN THE LIKENESS OF THIS HEAD", `c51.png`); `0000` and OK was accepted.

1 MB was not retried (the draft logged a bus error at `$ffff8e21`; PP's README says 2 MB).

## Memory and vectors in play

`phystop` `$200000`. The game is hand-written assembly loaded low: screen buffers `$2300` and `$a000` (`$392dc` shown, `$392e0` back), clean background pointer `$392e4`, code `$11d00`-`$2d500`, map `$3979e`, objects `$3e7aa`-`$46fa7`, players `$470fe`. Vectors: `$70` = `$18fa`, `$118` = `$1c42`, `$134` = `$2aa4e`. Zero runs in `busy1.bin`: `$7b37f`-`$f7fff` (511 KB), `$167cfa`-`$1d89f7` (462 KB): candidates for a payload, not proven free.

## Main loop and pacing

Top `$1252a`, bottom `$13340` (`beq $1252a`):

```
012548  jsr $1bf4         ; wait: tst.w $392cc / beq (flag set by the VBL $18fa..$1b34)
01254e  jsr $22f14        ; pacing + turn counter (below)
012554  cmpi.w #8,$39766  ; normal map view
01255e  jsr $1e7b2        ; copy the clean background (movem)
012584  jsr $1df44        ; terrain
012740  jsr $1334a
012746  tst.w $39796 / bne ; paused
01275c  jsr $2309a        ; people
012762  jsr $25652 / jsr $26644 / jsr $27faa / jsr $1fcce / jsr $29c7e / jsr $2a0b2
01278c  jsr $1bfe         ; flip: swap $392dc/$392e0, lsr.w #8, move.l d0,$ff8200.w, clear the flag
01279e  ...               ; keys, clicks (ui.md)
```

```
022f14  move.w $393fa,d0 / add.w $393fc,d0 / bne.b $22f2e     ; pointer not at (0,0)
022f22  cmpi.l #8,$392d4 / ble.b $22f14                       ; pointer at (0,0): wait for 9 VBLs
022f2e  clr.l $392d4                                          ; VBLs since the last pass
022f7e  move.l $3979a,d0 ... addi.l #1,d0 / move.l d0,$3979a  ; the game turn, if not paused
```

One turn and one redraw per pass, at most one pass per VBL, no other limiter. The only "slow" switch is the odd one above: with the pointer parked in the top-left corner a pass takes at least 9 VBLs. VBL counters: `$392d8` (long, free-running, `$1910`), `$392d4` (since the pass top, `$1b42`), flag `$392cc`.

## World turns per real second

`world_rate($3979c)` (low word of the turn), flips of `$ff8203`.

| Scene | People objects | 8 MHz: fps, turns/s | 16 MHz: fps, turns/s |
|---|---|---|---|
| start of the first conquest battle (`game_start.sav`) | 27 | 9.0, 8.90; 8.5, 8.45 | 16.75, 16.64 |
| 15,600 turns later, enemy towns in view (`busy1.sav`) | 147-228 | 6.0, 6.02; 6.1, 6.09 | 12.5, 12.48; 12.5, 12.42 |

```
8  {'vbls': 400, 'flips': 72, 'fps': 9.0, 'units_per_sec': 8.903}
16 {'vbls': 400, 'flips': 134, 'fps': 16.75, 'units_per_sec': 16.637}
8  {'vbls': 500, 'flips': 60, 'fps': 6.0, 'vbls_per_frame': 8.33, 'units_per_sec': 6.021}
16 {'vbls': 500, 'flips': 125, 'fps': 12.5, 'vbls_per_frame': 4.0, 'units_per_sec': 12.481}
```

**Verdict: coupled**, 2.05 times faster at 16 MHz, and 8.9 -> 6.0 turns per second on the same machine as the world fills. The busy scene was reached by letting the unmodified game play itself for 15,600 turns with Hatari's fast-forward (the computer opponent grew to 119 people objects, the player's side to 28). No divine effect was cast (the earth category was empty at this level); one land edit by click worked (`work/shots/g_effect1.png`). TT / Falcon not tried.

## Per-frame invariants

Twelve consecutive turns of `busy1` captured at `$12548`: the view did not move; of the 64 view cells, 0 or 2 changed their tile byte per turn; map-wide 28-52 of 4,096 cells changed any of their 4 bytes (mostly the occupant word).

```
turn 17905 map cells changed (any byte): 50 | in 8x8 view per byte [0..3]: [0, 2, 0, 0]
turn 17906 map cells changed (any byte): 42 | in 8x8 view per byte [0..3]: [0, 0, 0, 0]
turn 17907 map cells changed (any byte): 36 | in 8x8 view per byte [0..3]: [0, 0, 0, 0]
```
