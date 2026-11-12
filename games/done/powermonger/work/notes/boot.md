# Powermonger: boot path to the 3D map view (1 MB STE, TOS 1.62, `disks/protected.st`)

`tools/pm.py` (`PM(Hatari)`) implements it as `boot_to_game()`. Every stage waits for a screenshot gate (reference crops in `work/ref/`, git-ignored); there is no fixed delay except a 15 s initial wait.
The floppy is copied to the scratch dir and attached with `--disk-a`. `PM` also gives every instance its own `$HOME/.config/hatari/hatari.cfg`, so `hatari-shortcut savemem` writes to the instance's own `state.sav` and not to the shared `/tmp/hatari.sav`.

## Screens, in order (cold boot, times are wall clock, Hatari 2.6.1, real-time speed)

| # | Screen | Time | Gate / how to leave it |
|---|---|---|---|
| 1 | white screen (boot sector, `\AUTO\WAR.PRG` loads) | 0-15 s | none |
| 2 | black, A: LED on (loader reads the floppy by itself) | to ~40 s | none |
| 3 | intro: text "After a long journey...", castle, hall, captain, map, village pictures, then the credits loop on the logo | 40-80 s | **`xdotool key space` every 4 s skips the whole intro.** A left click did NOT skip it in two tries (see below). |
| 4 | "What Is Thy Name Oh Lord" (caret blinks) | ~80 s | gate `name_title.png`. **Typed input is accepted with xdotool keys** (`h.key('B')`... 0.25 s apart); the earlier failure came from typing before this screen existed and from `hatari-event keypress`, which the game does not see. Return accepts. An empty name gives the default name "Rustler". |
| 5 | "Welcome to the World of PowerMonger <name>": START NEW CONQUEST / CONTINUE CONQUEST / PLAY RANDOM LAND / LOAD DATA DISK | ~86 s | gate `opt_title.png`; click START NEW CONQUEST at ST px (160,85) |
| 6 | territory chart (195 territories, only the top-left island is open) | ~114 s | gate `chart.png`; hover the island at ST (20,18) (red rectangle appears), click |
| 7 | the 3D view is drawn behind a "Please Wait For The Protection Check" box, then the **copy-protection question** ("Between Pages 18-23: How many Houses/People in this land?", a map picture, four digit columns, two OK buttons) | ~155 s | gate `prot_bottom.png` |
| 8 | 3D map view (close-up map, overview map, captain portrait, command icons) | ~200 s | gate `game_hud.png` + main loop iterating |

### The protection question is answered from RAM
The question is not looked up in the manual: the game counts the objects of the generated land and compares your number with a word it computed itself.
* `$57ff8` (word) = question type (0 = Houses, 1 = People).
* `$5878e + 2*$57ff8` = the expected answer (counts made by `sub_00b892` over the object tables: houses table `$4f916` stride `$12`, people table `$51b66` stride `$32`).
* The check is `$b842: sub.w (a0,d1.w),d0 ; bne $b886` (`$b886` -> `$b9ac`: "Your answer is wrong... Demo mode now activated").
`boot_to_game` reads that word and clicks the arrow above each digit that many times: up arrows at ST x = 41/45/49/53 (thousands..units), y = 170; OK at (19,176). Values seen: 105 (houses), 128, 177 (people). They differ per run (the land is seeded from the video counter, `$b305`), the territory is the same island.

## Markers for "in the 3D map view"
* Screen: `game_hud.png` (compass, command icons) matches.
* RAM: `$2df70` (long) is the main-loop iteration counter, cleared at game start (`$13baa`) and +1 per loop pass (`$1302e`). `in_game()` = HUD gate AND `$2df70` grows over 1.5 s.
* Pointer position words `$1c492/$1c494` (ST px; 2 host px per ST px) let `goto_st(x,y)` close the loop on pointer motion.

## Facts that shape every test
* The game ends itself: after about iteration 940 of the first territory (`$57fec` = 432) the First Captain is defeated ("You have been defeated" screen, back to the option screen). Take snapshots early (map_idle is at iteration 18-33).
* While the Hatari debugger `echo` command is used, Hatari aborts (`Str_UnEscape` assertion): do not use it.
* A snapshot only restores in a scratch dir whose name has the standard `mkdtemp` length (the retargeting needs the new path not longer than the old), so every snapshot here was made from a normal `PM()` instance.
* The 4 s space polling reached the name screen at 80 s in 3 cold boots (80, 80, 80 s); whole `boot_to_game` took 203 s (run 1) and 202 s (run 2, snapshot script). Two cold boots from scratch succeeded (see baseline.md for the run log).
