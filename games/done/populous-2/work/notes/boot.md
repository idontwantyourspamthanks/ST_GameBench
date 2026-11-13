# Populous 2: boot

Superseded on 2026-11-11 by `baseline.md` ("Path to the game", "Memory and vectors in play"). The first draft's version of this note described the intro and the title credits as the game and is withdrawn. What survives from it:

- HAGA md5 `b34607ed9baecc5982a5a01ecaf5a3dd` (same file as Midwinter and Populous); `RUNME.TOS` unpacks with `tools/pp_depack.py` (`work/scratch/runme_unp.tos`: text `$440e`, data 22, bss 111206).
- 1 MB STE: the draft's log had `Bus Error reading at address $ffff8e21, PC=$13968` and a black screen (`work/shots/b00.png`-`b05.png`). Not retried; PP's README asks for 2 MB.
- The intro loop at `$2e9dc` compares `$fffc02` with `$39` once per VBL. Corrected: a held Space passes it (the draft wrote the byte from the debugger).
- `work/dumps/ingame.bin` is a dump of the intro, not of the game. Use `game_start.bin` and `busy1.bin`.
- PP's "deprot": the manual question is still shown; any answer is accepted.
