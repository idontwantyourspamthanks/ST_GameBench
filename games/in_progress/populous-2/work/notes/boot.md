# Populous 2: boot

HAGA md5 `b34607ed9baecc5982a5a01ecaf5a3dd` (same file as Midwinter and Populous). RUNME.TOS unpacks (text `$440e`, data 22, bss 111206). Same delivery shape as Midwinter. PP's README says 2 MB minimum and that the manual question was removed ("Deprot").

## 1 MB does not boot

1 MB STE, GEMDOS C:, TOS 1.62: `log.txt` of that run records `Bus Error reading at address $ffff8e21, PC=$13968` and the screen stays black (`work/shots/b00.png`–`b05.png`). `$ffff8e21` is not the shifter. The GEMDOS folder itself is fine: the same folder at 2 MB reaches the game.

## 2 MB

Hardware screen, space, then a map flyover. That flyover is not the game. Its loop at `$2e9dc` waits on a VBL flag and then polls the keyboard data register directly:

```
2e9e0  jsr  $2e9aa          ; spin until VBL sets $345bb
2e9e6  bsr  $2ea52          ; unrolled rotate
2e9f0  cmpi.b #$39, $fc02.w ; absolute short = $fffffc02
2e9f6  beq  $2e9fa
2e9f8  bra  $2e9e0
```

`$118` is still TOS (`$00e03ca0`), so TOS reads `$fffc02` in the ACIA interrupt and the poll never sees the `$39`. `hatari-event keypress 57` and an xdotool space did not leave the screen. Writing `$39` to `$fffc02` from the debugger did, and the next stage (`$2f4b2`) waits 300 VBL (`cmp.w #$12c`) unless that byte is seen again. After several writes the game is on the map with the query panel open: `work/shots/skip1.png`.

In play: VBL vector `$70` = `$0002e9b4`, screen `$ff8200` = `00 0f 00 80` (base `$f0000`). Marker: `$2e9b4` is `50 f9` (`st.b $345bb`) and `$ff8201` = `$0f`.

Dump during the flyover: `work/dumps/ingame.bin` (2 MB; the name predates the real game screen). The in-play profile below was taken on the query-panel screen, not from that dump. The snapshot attempt blocked Hatari on its overwrite question and was discarded.
