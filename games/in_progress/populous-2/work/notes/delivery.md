# Populous 2: patch delivery (pop2patch.py), free RAM, protection, credit, floppy

2026-11-11. Tool `tools/pop2patch.py` (design copied from Midwinter 2's `mw2patch.py`), patches in `patches/`
(format and mechanism: `patches/README.md`). Machines: Hatari 2.6.1, STE TOS 1.62, Mega STE TOS 2.06 / 1.62,
TT TOS 3.06, Falcon TOS 4.04. Nothing here touches the originals; all builds are in `build/` (git-ignored).

## 1. What the game actually is (the fact the design rests on)

`RUNME.TOS` unpacks (LZ, `tools/pp_depack.py`) to text `$440e`, data 22, bss 111206. Trace of a cold boot
(`--trace gemdos`, 2 MB STE):

```
GEMDOS 0x3D Fopen("HAGA")                 ; -> bss at $4644, copied to $1f8000
GEMDOS 0x3D Fopen("FP2273.HST")           ; cover picture (STE; LP...HST on ST, P2240R.BMP on TT/Falcon)
GEMDOS 0x3B Dsetpath("FILES")
GEMDOS 0x4B Pexec(0, "P2CR.TOS", [32]"1") ; the Bullfrog credits program ($2e90c), runs and Pterm0s
GEMDOS 0x00 Pterm0() at PC 0x2E980
GEMDOS 0x3D Fopen("P2M.FIC") -> Fread(64, 104830, 0x101000)
GEMDOS 0x3D Fopen("P2D")     -> Fread(64, 418679, 0x101000)   ; at PC 0x1F9022 (PP's service)
```

* `P2M.FIC` = 32-byte header + PP's LZ stream, unpacked **to `$1770`** by the stage block (RUNME text
  `$386`-`$392`, `lea $1770.w,a4`): 498,704 bytes (`$79c10`), consumed exactly (104,798 of 104,798). Compared
  with `work/dumps/game_start.bin` at `$1770` it differs only in runtime data and at PP's four patch sites
  (`$1cf8`, `$14a88`, `$2cc98`, `$36efc`) — so this is the game image every site is verified against.
* `P2D` = 418,679 bytes read whole into `$101000`; PP's stub at `$140` serves "file N" out of it (offset table
  at `$196`: 25 cumulative offsets ending at `$66377` = the file length).
* The game is at `$1770`-`$7b380`; screens `$2300`/`$a000`; map `$3979e`; stack `$12522`.

## 2. The delivery mechanism (evidence: `pop2patch.py verify`, cold boots)

RUNME edits (unpacked image offsets = text offsets), all verified byte-for-byte by `verify`:

```
RUNME stage hook  text $0318: 46fc2700                    -> 6100 <bsr.w copy>   ; the stage block's move.w #$2700,sr
RUNME PP tail     text $03da: 21fc00001c420118 4ef81770   -> 4ef9 00080000 4e71*3 ; PP's move.l #$1c42,$118.w + jmp $1770.w
RUNME bss pc-relative references: 4 `lea d(pc),aN`, no others   ; each becomes movea.l d(pc),aN + 2 relocated pointer slots
```

* The payload (`$80000-$87fff`, 32 KB) rides in RUNME's data segment; a 30-byte `copy` routine (appended there,
  entered from text `$318`) copies it to `$80000` **before** the unpack overwrites RUNME's TPA, then replays the
  displaced `move.w #$2700,sr`.
* The trampoline (`patches/core.s`, `$80000`) replays PP's `move.l #$1c42,$118.w`, presets `P2PF` at `$7fff8`,
  verifies every site, applies all or none, sets `P2PO`, and ends `jmp $1770.w`.
* The data segment grows by 30 + 8 + $8000 = 32,806 B: the bss, the stack top (`$6`), the Mshrink size and the
  HAGA load address all move with it; the four `lea d(pc),aN` into the bss are rewritten (a 16-bit pc
  displacement cannot span 32 KB); `build_runme` re-encodes the reloc table and round-trips it.
  No d16(pc) operand is left addressing the bss (`verify` fails the build otherwise).

Cold boot, 2 MB STE, zero-patch build: `m $7fff8` = `50 32 50 4f` (`P2PO`), `m $80000` =
`21 fc 00 00 1c 42 01 18` (the trampoline) — the payload arrives intact and the marker is set, on the first
attempt.

## 3. Free RAM: the pattern test (`tools/p2ptest.py`)

At the game entry ($1770, a debugger `:once :file` breakpoint that then `loadbin`s three pattern images),
long at address A := `A*2654435761+$1234567` was written into the candidates and compared after each step:

| Range | Why a candidate |
|---|---|
| `$7b380-$7fff7` | zero in the busy dump; directly above the game image (ends `$7b380`), below `$80000` |
| `$88000-$f7fff` | above the payload, below TOS/PP memory; zero in the busy dump |
| `$167d00-$1d89f7` | zero in the busy dump (the start of PLAN.md's `$167cfa` candidate, aligned) |

Steps: main menu -> first conquest battle -> 12,920-15,293 turns of fast-forward play (`--fast-forward on`,
~170 turns/s) -> all six effect categories with their five slots and clicks (volcano, raised land) -> HAGA
statesave (keypad `/`) -> RESTART MAP -> QUIT MAP -> new conquest -> CUSTOM GAME (a random landscape, i.e. a
level change and a full regeneration).

Result, STE 2 MB (x) and STE 4 MB (y) — identical:

```
[ste_4mb] main menu reached; marker 'P2PO'; credit screenshot work/shots/credit_menu_ste_4mb.png
[ste_4mb] menu: payload intact
    $7b380-$7fff8: 0 longs changed
    $88000-$f8000: 0 longs changed
    $167d00-$1d89f8: 0 longs changed
[ste_4mb] in play, turn 175                     (12,920 turns busy, then effects, statesave, restart, conquest, custom)
[ste_4mb] HAGA statesave: GS00.TOS 1049310 bytes
[ste_4mb] RESULT: ALL INTACT
```

Every one of the six dumps (menu, play, busy, effects, statesave, restart, conquest2, custom) reported
`0 longs changed` for all three ranges and `payload intact`. The 2 MB run (same script, done interactively
first) gave the same result at each of its eight dumps, including at 15,293 turns with 100+ people objects.

**Conclusion: `$80000-$87fff` is free for the payload at 2 and 4 MB** through play, effects, save and level
changes. It is also below `$100000`, so HAGA's statesave (which writes the first 1 MB of RAM) carries it.

## 4. Protection: what the game asks and what it checks

* **The manual question is still asked** ("HOW MANY STATUES HAVE BEEN BUILT IN THE LIKENESS OF THIS HEAD",
  `work/shots/c51.png`); PP's own patch makes `cmp.w d1,d2` at `$14a86` followed by `bne` into `bra` — any
  answer is accepted (`0000` + OK works). No harm to play, so **no patch of ours**.
* **No vector/trap protection found.** Populous 1's trap is a `Supexec` read of the long at `$24` compared
  with `$2a560421*2`. Populous 2 has no `trap #$e`-based `Supexec` call in its code, no absolute read of the
  vectors at `$08`-`$bc` in the linear disassembly of `$1770`-`$3e000`, and no second comparison with a key.
  Its only self-check is the PAL check (below) and the manual question.
* **PAL check (new finding, matters for the 50/60 Hz work):** at `$1836`-`$1840`, `btst.b #1,$820a.w` /
  `bne.w $186e`; a 60 Hz machine falls through to `$1840`, which prints "SORRY PAL MACHINES ONLY"
  (`work/shots/pal_only_megaste_60hz.png`) and loops at `$1850` forever. Patch `pop2_ntsc` (`$183c`,
  `default: no`) makes the branch unconditional. **But** forcing past it is not enough: at 60 Hz the game then
  draws garbage and dies (bus errors at `$201e` writing to address 0), on TT and Mega STE alike, with the
  untouched game as well as with the patches. So 60 Hz support needs real work (the tick/display job), not a
  branch byte.
* No `$24`-style Armageddon trap: the 4 MB busy run played 12,920 turns and levels changed without it.

## 5. Release credit (`pop2_credit`, `default: yes`, site `$15338`)

Site: the `jsr $1b9a.l` (pointer-hide counter) in the main-menu routine `$15304`, right after it has copied
the title picture into **both** screen buffers (`$392e0`, `$392dc`); the blob draws into both, so the line
survives the per-pass picture copy and both flips, and then `jmp $1b9a.l` (the displaced call) returns to
`$1533e` as before. Text: `v<VERSION> enhanced by dad_prg` from the `; version:` header (the single place the
release version exists; `pop2patch.py version` = `1.0`), drawn with a 3x5 own font (3x5 small-caps; the game's
own 8x8 font would be 216 px wide, not discreet) in palette colour 3 (the menu's dim tan), centred at
(112,158)-(216,162) in the empty lower part of the slate panel. Only glyph pixels change (bset/bclr in all
four planes). Screenshots: `work/shots/credit_menu_hd_2mb.png` (2 MB STE), `credit_zoom.png`,
`credit_menu_ste_4mb.png`, `credit_menu_megaste4mb_tos162.png`, `credit_menu_floppy_2mb.png`,
`credit_menu_tt4mb_60hz.png`.

## 6. In-game save / load (why "saving must work" is not met, and what it would take)

* **Broken in PP's build, unpatched**: opening the game requester and clicking SAVE GAME crashes the
  untouched game at once (`Bus Error reading at address $5c40c82, PC=$5c40c82`, reproduced twice on
  `game_start.sav`); PP's README says so in words ("Ingame save/load works not. Use HAGA statesaves").
  Cause: PP replaced the game's whole disk layer `$36efc` (a command dispatcher: d0 = 0 read, 1, 2, 3, 5 ...,
  a0 = file name, a1 = buffer, `movem.l d1-d7/a0-a6`) by `jmp $140`, a stub that only knows "copy file number N
  out of P2D in RAM" and ignores d0 — so every other operation (the save/load requester's directory and file
  calls at `$2cb0e`, `$2cbe4`, `$2cc58`) is answered from the wrong table.
* **HAGA statesave (keypad /)** works on the HD build: it writes `C:\GS00.TOS` (1,049,310 bytes =
  the first 1 MB of RAM + a header) and writes further slots as `GS00.TOS`, `GS01.TOS`...; on a floppy it
  writes `..\GS00.TOS` to the root. **It cannot fit a floppy** (1 MB into 43 KB free), and on the floppy the
  write silently fails after the first chunks.
* Prototype patches `pop2_save_a` (`$140`) + `pop2_save_b` (`$20e`, `default: no`): the stub entry serves
  PP's RAM copy only when the file-by-number function `$2cc98` has just announced a file number (a flag at
  `$802f0`), and otherwise re-executes the displaced prologue and jumps to `$36f00` — the game's own FAT12 +
  FDC driver. With them, SAVE GAME opens the file requester and the game **no longer crashes** (before: crash
  on the first click) and the driver reads drive A. A completed save onto a real FAT floppy was **not**
  achieved in Hatari 2.6.1 within this pass: the requester's directory read needs the disk re-inserted after a
  snapshot restore (`hatari-option --disk-a`), and the run then either reports DISK FILE ERROR or stops
  responding. Remaining work: the requester's input handling and the FDC exchange, or a save path through
  PP's own file service.
* **Recommendation:** keep saving on the HD build (HAGA statesave) and say so in the floppy README; the
  floppy build should not claim in-game saving. If a floppy save is required, the compact route is to have
  `$36efc`'s write commands go through PP's service (Fcreate/Fwrite to `A:\POP2SAVE.NNN`) — that is a
  re-implementation of the save format, not a patch.

## 7. Floppy build (`build --floppy`)

One bootable 720K .st (`build/floppy/Populous2_boot.st`), FAT12 via mtools: `AUTO\RUNME.PRG` (the patched
RUNME), `HAGA`, `FP2273.HST`, `FILES\P2CR.TOS`, `P2D`, `P2M.FIC` — 681,179 bytes, 43,008 free. RUNME's file
names are relative, so it finds everything on drive A (trace: `Pexec(0, "\AUTO\RUNME.PRG", ...)` ->
`Fopen("HAGA")` -> `P2CR.TOS` -> `P2M.FIC` -> `P2D`). Only the STE cover picture fits; RUNME opens
`FP2273.HST` on an STE/hi-colour machine, `LP2273.HST` (name rewritten in its data) on a plain ST and
`P2240R.BMP` on TT/Falcon, and simply returns when the open fails, so the other two machines get no cover
picture and the game still runs ([INFERENCE] from `$9b4`-`$9c2` / `$40ce`: `bmi -> addq.l #4,a7 / rts`).

Result (STE 2 MB, TOS 1.62, cold boot from drive A): reaches the main menu (credit visible,
`work/shots/credit_menu_floppy_2mb.png`), `P2PO` set, first conquest battle in play
(`work/shots/play_floppy_2mb.png`, turn 175). Keyspace: drive A; nothing else is needed.

## 8. Machine status

| Machine | Build | Result |
|---|---|---|
| STE 2 MB, TOS 1.62 | HD, default set | play, `P2PO`, credit visible (`credit_menu_hd_2mb.png`) — **acceptance** |
| STE 4 MB, TOS 1.62 | HD, default set | play, `P2PO`, credit, full pattern test intact (`credit_menu_ste_4mb.png`) — **acceptance** |
| Mega STE 4 MB, TOS 1.62 (50 Hz) | HD, default set | play (turn 225), `P2PO`, credit (`credit_menu_megaste4mb_tos162.png`, `play_megaste4mb_tos162.png`) — **acceptance** |
| Mega STE 4 MB, TOS 2.06 (US, **60 Hz**) | HD, default set | "SORRY PAL MACHINES ONLY" — the untouched game's own check (`pal_only_megaste_60hz.png`). With `pop2_ntsc`: menu + credit, then the game draws garbage in play — the same with a zero-patch build forced past the check, so not our patches |
| TT 4 MB, TOS 3.06 (60 Hz) | HD, default / zero | menu + credit, `P2PO`; entering the game: garbage + bus errors at `$201e` (address 0) — identical with zero patches, so pre-existing at 60 Hz |
| Falcon 4 MB, TOS 4.04 (50 Hz) | zero-patch build | **play** (turn 321) — the untouched game + our staging (`play_falcon4mb_nopatch.png`) |
| floppy, STE 2 MB | `build --floppy` | boot, menu, credit, play — **acceptance** |

The 60 Hz finding is the important one for the tick work: the game assumes 50 Hz (both its own PAL check and
its drawing), so "50/60 Hz" support has to be part of that job.

## 9. Reproduce

```
python3 tools/pop2patch.py verify                 # ALL OK
python3 tools/pop2patch.py build                  # build/hd
python3 tools/pop2patch.py build --floppy         # build/floppy/Populous2_boot.st
python3 tools/p2ptest.py --mem 2048               # free-RAM pattern test + cold boot gates (STE 2 MB)
python3 tools/p2ptest.py --mem 4096               # ... 4 MB
tools/package.sh                                  # dist/ zips
```
