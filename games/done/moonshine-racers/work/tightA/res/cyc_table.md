### driving (race_start)
| variant | no speech: mean (n) | delta | VBL/pass | speech: mean (n) | delta | VBL/pass | max pass |
|---|---:|---:|---:|---:|---:|---:|---:|
| current default (reference R) | 491171 (83) |  | 3.065 | 517265 (151) |  | 3.228 | 610324 |
| ta_erase (+ta_init)  [erase+glyph, no face] | 490013 (83) | -1158 | 3.058 | 515761 (151) | -1290 | 3.218 | 610336 |
| ta_erase+ta_init+ta_face | 489983 (83) | -1188 | 3.058 | 513101 (153) | -4371 | 3.202 | 604760 |
| speech set: erase+face+glyph (pixel-identical) | 489843 (83) | -1328 | 3.057 | 511758 (153) | -5572 | 3.193 | 604196 |
| speech set with ta_facestat (VISIBLE) | 489843 (83) | -1328 | 3.057 | 509579 (153) | -7791 | 3.180 | 604260 |
| ta_ymw | 489787 (83) | -1384 | 3.056 | 515684 (152) | -1474 | 3.218 | 609000 |
| ta_rb | 488189 (83) | -2982 | 3.046 | 514378 (153) | -3120 | 3.210 | 606484 |
| ta_rb + ta_rb0 | 486658 (83) | -4513 | 3.037 | 512825 (153) | -4520 | 3.200 | 605016 |
| ta_nomouse (risk) | 482857 (83) | -8314 | 3.013 | 508475 (156) | -8517 | 3.173 | 600872 |
| interrupts: rb+ymw+nomouse | 478323 (83) | -12848 | 2.985 | 503155 (148) | -12819 | 3.140 | 589980 |
| ALL pixel-identical: speech set + rb + ymw + nomouse (no rb0) | 477201 (83) | -13970 | 2.978 | 498697 (151) | -18331 | 3.112 | 589536 |
| ALL pixel-identical incl. rb0 | 475584 (83) | -15587 | 2.968 | 497609 (152) | -19525 | 3.105 | 588068 |
| ALL with ta_facestat (VISIBLE), no rb0 | 477491 (83) | -13680 | 2.980 | 496724 (152) | -20442 | 3.100 | 589572 |
### standing (race_grid)
| variant | no speech: mean (n) | delta | VBL/pass | speech: mean (n) | delta | VBL/pass | max pass |
|---|---:|---:|---:|---:|---:|---:|---:|
| current default (reference R) | 414960 (74) |  | 2.589 | 418016 (159) |  | 2.608 | 461460 |
| ta_erase (+ta_init)  [erase+glyph, no face] | 413230 (74) | -1730 | 2.579 | 416896 (159) | -1120 | 2.601 | 459664 |
| speech set: erase+face+glyph (pixel-identical) | 413230 (74) | -1730 | 2.579 | 413291 (159) | -4725 | 2.579 | 459768 |
| speech set with ta_facestat (VISIBLE) | 413231 (74) | -1729 | 2.579 | 411050 (158) | -6988 | 2.565 | 459812 |
| ta_ymw | 414292 (74) | -668 | 2.585 | 417406 (159) | -610 | 2.605 | 460864 |
| ta_rb | 411944 (74) | -3016 | 2.571 | 415024 (158) | -3014 | 2.590 | 458440 |
| ta_rb + ta_rb0 | 410970 (74) | -3990 | 2.564 | 414024 (159) | -3992 | 2.584 | 457484 |
| ta_nomouse (risk) | 407898 (74) | -7062 | 2.545 | 410947 (158) | -7091 | 2.564 | 454388 |
| ALL pixel-identical: speech set + rb + ymw + nomouse (no rb0) | 402452 (74) | -12508 | 2.511 | 402576 (159) | -15440 | 2.512 | 449180 |
| ALL pixel-identical incl. rb0 | 401474 (74) | -13486 | 2.505 | 401595 (159) | -16421 | 2.506 | 448196 |
| ALL with ta_facestat (VISIBLE), no rb0 | 402452 (74) | -12508 | 2.511 | 400339 (159) | -17701 | 2.498 | 449224 |
