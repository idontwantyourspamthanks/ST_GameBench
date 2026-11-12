# Populous 2: the manual question ("ZEUS ASKS: HOW MANY STATUES ...") and `pop2_noquest`

2026-11-12. Patch `patches/pop2_noquest.s` (site `$20a02`, 22 bytes, `; default: yes` after the gates below), driver `tools/p2noquest.py`.
Tags: **[disasm]** `tools/m68dis.py work/dumps/game_start.bin` (the unpatched game + PP's four patches); **[obs]** raw output in `work/gates/`;
**[INFERENCE]** not proven. Screenshots: `work/shots/noquest/`.

## 1. Where the screen is called, and the only path into it [disasm]
The screen is one routine, `$148b2` (`movem.l d0-d7/a0-a6,-(a7)` at `$148b2`, `rts` at `$14ac4`). One caller:
```
020a02:  4a7900039612         tst.w    $39612.l          ; the "answered" flag
020a08:  660e                 bne.b    $20a18
020a0a:  4a790003960a         tst.w    $3960a.l          ; the last palette fade went to a real palette
020a10:  6706                 beq.b    $20a18
020a12:  4eb9000148b2         jsr      $148b2.l          ; <- the question
020a18:  082b0004000d         btst.b   #$4, $d(a3)       ; the handler goes on drawing the object
```
`$20a02` is the draw handler of ONE object kind, reached through the per-kind jump table at `$2078e` (`020782 move.w $2078e(pc,d2.w),d2` /
`020786 jsr $2078e(pc,d2.w)`, table word `$0274` -> `$2078e+$274 = $20a02`); in the cold run the stack at the question holds `0002 0a18` (return
address after the `jsr` at `$20a12`) and `0002 078a` (return after `$20786`) [obs: `r` + `m a7 96` at pc=$148b2].
`work/gates/noquest_callers.txt`: the whole game image has exactly one 32-bit reference to `$148b2` (`$20a14`, inside that `jsr`) and no pc-relative
branch to it (word-offset tables cannot be excluded by a scan: [INFERENCE]; but the breakpoint on `$148b2` counted 0 hits in every `noquest` run, see 4).
Consequence: it is not tied to a menu path. It fires **once per program run**, the first time a visible frame (`$3960a != 0`) draws an object of that
kind with `$39612 == 0`. Reference run, conquest: hit at turn 7, 1 hit in total; custom game: also turn 7, 1 hit
(`work/gates/noquest_cold.txt`, `ref_ste2_conquest`, `ref_ste2_custom`). Deity creation (CREATE YOUR DEITY and back) and the LOAD GAME requester never reach it
(0 hits, flag stays 0). After the question `$39612 = 1` and nothing ever clears it (xref below), so there is no periodic repeat.
LOAD GAME: in PP's build the requester only reports "DISK FILE ERROR" or resets the machine, in the **unpatched reference too** (`e_load*.png`,
`ref_ste2_load`; the reset appeared in one run of each build, so it is not ours); a loaded game cannot reach play, so that path cannot be exercised either way.

## 2. The state the success path leaves [disasm]
```
$39612   written only at 014aac: move.w #$1, $39612.l       (xref: 014aac write, 020a02 read - nothing else)
$3960a   $22192 clr.w / $221a0 move.w #1 (the palette fade $2218a: "to $36c82 = black" leaves it 0).  The routine's last act (014aa6) is
         jsr $2218a with a3 = $36c82, a FADE TO BLACK: $3960a = 0, and the game's next fade-in sets it to 1.
$11d50   saved to $39636 at 0148bc, restored at 014a8c: net unchanged ($39636 is a pure save slot: written before read at 0148bc / 015c6c / 029b66)
files    0148d8 jsr $2cc98 with d0 = 8, 0148e2 d0 = $1c (the head picture and its table), then $2d326 at 014ab4 reloads the game's graphics
         (files $4737c+4, $17, $18, +$f, +$13, +0)
random   the head is chosen from $8207/$8209 (the video counter, 0148ea-0148f4) + $392d0 (read ONLY here, 0148f4); the routine's own code stores
         only to its scratch ($149e8, $392cc, $11d50/$39636, $39612) and calls library routines; that no callee draws from the world RNG is
         [INFERENCE] from the code, supported by the replay gate below (world identical from turn 11; [INFERENCE] the world RNG state lies inside `$39600-$473ff`, not located)
```
So skipping must set `$39612 = 1` and nothing else of the world: no random numbers are consumed, nothing in the world (`$39600-$473ff`) is stored
by the screen except the flag and `$3960a` (fade, see 4).

## 3. The patch
`$20a02`: `33fc 0001 0003 9612` (`move.w #1,$39612.l`) + `600c` (`bra.s $20a18`) + nops over the original 22 bytes. The flag is set at the same place
and by the same instruction as the success path's, every time the handler runs (8 bytes; replaces a 14-byte test chain). No data patch: `$39612` is
game memory the game initialises, so a RAM write at boot would depend on the game's own clearing; the code patch cannot be undone by it.

## 4. Gates (all raw output in `work/gates/`)
**Cold boots, no question** (`tools/p2noquest.py cold`, screenshot after every step, a debugger breakpoint on `$148b2` counts every hit; reference =
`build/nq_ref` = the default set minus noquest; `build/nq_hd` / `nq_floppy` = default + noquest; `noquest_cold.txt`):
| run | question hits | flag `$39612` at play | turn counter moves |
|---|---|---|---|
| ref, STE 2 MB, conquest | 1 (turn 7; `ref_ste2_conquest_06_question.png`, OK clicked) | 1 | yes |
| ref, STE 2 MB, custom | 1 (`ref_ste2_custom_05_question.png`) | 1 | yes |
| noquest STE 2 MB, conquest | **0** | 1 | `0x11c -> 0x133` |
| noquest STE 2 MB, custom game | **0** | 1 | `0xf6 -> 0x10c` |
| noquest STE 2 MB, deity creation | 0 (no play) | 0 | - |
| noquest STE 2 MB, LOAD GAME | 0 (requester only, see 1) | 0 | - |
| noquest Mega STE 4 MB TOS 2.06, conquest | **0** | 1 | `0x132 -> 0x149` |
| noquest TT 4 MB TOS 3.06 `--mmu true`, conquest | **0** | 1 | `0x13e -> 0x154` |
| noquest floppy STE 2 MB, conquest | **0** | 1 | `0x11c -> 0x133` |
| noquest floppy Mega STE 4 MB, conquest | **0** | 1 | `0x133 -> 0x149` |
| packaged `build/hd` and `build/floppy` (after `package.sh`), STE, conquest | **0** | 1 | `noquest_cold_pkg.txt` |

**pop2patch verify:** `noquest_verify.txt` (`verify: ALL OK`; the 22 original bytes match the unpack and `game_start.bin`).

**p2tick ab** (the pass-top world by turn + T/R frames, patched set + `pop2_noquest` live vs unpatched, 130 turns, 8 MHz):
`busy1`: IDENTICAL (134 tops, 0 differ), `game_start`: IDENTICAL (239 tops, 0 differ), `--neg` (patched run does not walk) DIFFERS
(`noquest_ab_busy1.txt`, `..._game_start.txt`, `..._busy1_neg.txt`). The snapshots hold the flag already set, so this only shows that the patch does not
perturb a run that never asked.

**The world after the skip vs after a normal answer** (the real gate; `tools/p2noquest.py pre | replay | compare`):
`pre` boots the still-asking build to PROCEED and freezes the game at the instant before the question: a hook at the first entry of `$20a02` with
`$39612 = 0, $3960a = 1` writes `60fe` (`bra.s *`) over the `bne` at `$20a08` (a hook at `$20a02` cannot touch the instruction at the PC), the game spins,
`savemem` -> `work/snapshots/pre_question.sav` (turn 7, `$20a08 = 0x60fe`, flag 0). `replay` restores it twice: **ask** writes the original 22 bytes and
`r pc=$20a02`, the question appears (`work/shots/noquest/replay_ask_question.png`), OK is clicked; **skip** writes pop2_noquest's 22 bytes and `r pc=$20a02`.
Both record the world `$39600-$473ff` at EVERY pass top (`$1254e`) up to turn 137 and the whole 2 MB RAM at the first pass top and at turn 137.
* **Determinism control:** two ask runs: `world by turn: IDENTICAL`, full RAM `0 bytes differ` at both dump points; skip vs skip + one poked byte (`$3e100`):
  differs in exactly that byte at all 131 turns and in the RAM dumps (`noquest_replay_compare.txt`): the gate sees one byte, the runs are bit-exact.
* **ask vs skip, turns 11-137: IDENTICAL** (127 turns, the same four masks p2tick uses). **Turns 7-10 differ in one byte, `$3960b`** (A 0, B 1) = `$3960a`,
  the fade flag: the answered run ends the screen with a fade to black (section 2), the game then fades in again and the flag is back at turn 11;
  the skipped run never faded.
* **Full RAM at turn 137 (ask vs skip), 43 ranges, 2,288 bytes, all explained** (`noquest_replay_compare.txt`):
  - `$020a02-$020a18`: the patch itself (22 B).
  - `$0149e8-$0149eb`: the question's own digit/head variables (3 B). `$01c344-$01c744`: the dialog text buffer (the question's text vs the previous
    dialog's); `$149`: the immediate of PP's stub `move.w #N,d0` at `$146`, "last file requested" (A: file 0 after the `$2d326` reload; B: `$e`); `$2cdb4`: [INFERENCE] the
    file table's size word of that last reload; `$053c40-$054078` (1080 B): leftover of the head picture load (zeros in B, no world effect in 130 turns).
  - `$0392d0-$0392dc`, `$082806`, `$082823...`: VBL-derived counters (A spent 330 VBLs = 6.6 s in the question: `$392d0` A `$1159` B `$100f`, delta `$14a` = 330;
    the tick's accumulator at `$82806`, same delta); `$0393f7-$0393f9`: previous pointer position words.
  - `$004971-$005555` (117 pixels, a 13 x 20 px sprite at (171..183, 61..80)) in the **back** screen buffer `$2300`; the shown buffer `$a000` is identical [obs:
    decoded both buffers]. [INFERENCE] the back buffer holds the frame from before the last flip, which depends on the pass history (A spent two extra passes
    around the question); the world and the shown frame are the same.
  - nothing else. The first-pass-top dump (`ram_first.bin`) also contains the whole screen buffers (A: the picture left by the question, B: the game's frame), as expected.

## 5. Reading
Skipping the screen takes the success path's one lasting state change (`$39612 = 1`) and no random number is drawn by the screen, so the world after
turn 10 equals that of an answered run bit for bit (127 turns compared by hash of the whole world region, plus all of RAM at turn 137 with the above
explained differences). What the player sees differs in that there is no fade to black and back after the (non-existent) question.
