# Nebulus: harness, boot chain, and the traps (lead notes)

Hatari 2.6.1, STE TOS 1.62, 1 MB, 8 MHz unless stated. Tool: `tools/nebulus.py` (lead-owned).

## 1. Why Hatari's GEMDOS drive fails, and what works
Gamex/`START.TOS` re-runs the disk's root sector to install a private HD driver and then `Pterm(0)`s when
there is none (same chain as Hunter: `games/done/hunter/work/notes/boot.md` §1). So `tools/nebulus.py` builds
a 16 MB FAT16 **ACSI** image whose root sector is HDDRIVER's boot code (`gamebench/hd/hddriver_root.bin`,
user-supplied) + our partition table, whose partition boot sector is HDDRIVER's loader
(`hddriver_pboot.bin`) + the mkfs BPB, and which carries `HDDRIVER.SYS`, the game files and a `DESKTOP.INF`
that autoruns `C:\START.TOS`. Verified: HW-detect screen → loader pictures → the game's title → a running tower.

## 2. Boot sequence as seen (before the game's title loop)
| VBL (cold) | screen | notes |
|---|---|---|
| ~0-500 | HDDRIVER banner, then the Gamex HW-detect text screen ("Machine: STE, TOS ver 1.62, 1MB, GAMEX: key F9") | advances on its own after ~20 s |
| ~500-1500 | loader pictures (PP's title/credits, fading) | advance on their own; space speeds them |
| ~1500+ | the game's own title: NEBULUS logo, "Design, Programming & Audio-Visuals by John M Phillips ©1987,8 Hewson", `Mission #1`, `Sound On`, Options key list (F1/F2 1 or 2 player, F3/F4 sound, F5/F6 50/60Hz, F7/F8 Mission) | RAM marker: `$3d00f` = "Higl" ("High Scorers") once the game data is resident |
| | the attract cycle then alternates the title with the **High Scorers** table (`00046420 JMP`, `00050000 JMP`, `00030000 JMP`, `00010000 JMP`) | this fooled the lead for a while: screen changes are NOT proof of input |
Starting a game: **one space at ~16 s** (ends the HW screen), wait for the marker, `Right` 0.5 s,
`Right Ctrl` (fire, `--joy1 keys`) 1.0 s. **Six spaces during the loader leave the title unable to start a
game by fire** (measured by NebTrainers, and reproduced by the lead: timer stays 0). Do not press keys after
the game's title is up.

## 3. In-tower markers (verified)
- Timer: words `$3ad98/$3ad9a/$3ad9c`, each digit ×8; `00 20 00 00 00 00` = "t-400" at tower 1 start, then
  counts down (`00 18 00 48 00 45` = 399 and a bit).
- Tower index `$3390c` (0 = tower 1). Key/joy state byte `$38498` (`$1d` = fire+right, `$80`/`$9d` = Ctrl
  make/break). The game's IKBD handler is `$384fc`, hooked by Gamex via `jmp $200`.
- Title loop `$3d6c4`/`$3853a`, fire flag `$338f0`; timer tick `$3b0a4` gated by `$33938`; per-tower initial
  time table `$3ad9e`; enemy struct-of-arrays `$33944` (6 words/field, stride `$c`, state `+$48`).

## 4. Measurements
- `fps()` with `($ff8201).b`: 22.05 fps in the tower at 8 MHz over 1000 VBL (441 flips, 2.27 VBL/frame);
  ~17-18 fps on the title/high-score screens; 50.25 fps on a loader picture. The flip routine is
  `sub_03868a` (game code `$3868a`): it draws through `$3822c` and then writes BOTH `$ff8201` (hi) and
  `$ff8203` (mid) from `$38759`/`$3875a`, so the harness default `($ff8201).b` does see every flip
  (from `work/train/dis_33000_40000.txt`). What the ~22 fps means for gameplay (frame skip vs 2.27 VBL
  work per frame) is NebBoot2's task C.
- Baseline: `work/snapshots/1mb_tower.sav`, `work/dumps/tower_1mb.bin` (2 MB), `work/shots/tower_baseline.png`.

## 5. Gotchas
- A restored memstate does not keep `--joy1 keys`; `Nebulus(snapshot=...)` adds it explicitly (verified).
- The `h.key()` path needs long holds (~0.5-1 s) at the title; 0.15 s does nothing visible.
- `fps()` on a menu is not a gameplay number.
