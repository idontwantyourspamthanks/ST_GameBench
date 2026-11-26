## T1 cycles per frame by class (slot net time = dispatch + draw; ISR time excluded), mean over traced frames
| scene | frames | player (slot12) | player2 (slot49) | opponents 13-15 | scenery type 0 | scenery type 1/3 composites | inactive slots | stage total |
|---|---|---|---|---|---|---|---|---|
| race_grid | 142 | 36,149 | 22,017 | 15,644 | 91,326 | 41,254 | 6,858 | 213,250 |
| race_start | 120 | 35,160 | 21,713 | 38,532 | 70,155 | 52,964 | 6,254 | 224,778 |
| race_up | 120 | 35,415 | 21,326 | 15,973 | 101,833 | 46,689 | 6,137 | 227,373 |
| race_drive | 78 | 33,475 | 21,883 | 14,734 | 81,227 | 53,734 | 6,243 | 211,296 |

## T2 type-0 single-sprite calls per frame by size class (columns x aligned/shifted), visible rows, mean kernel cycles
| scene | cols | x&15 | calls/frame | mean visible rows | mean kernel cycles/call | kernel cycles/frame |
|---|---|---|---|---|---|---|
| race_grid | 1 | aligned | 0.17 | 10.0 | 1,834 | 310 |
| race_grid | 1 | shifted | 7.90 | 12.0 | 4,757 | 37,587 |
| race_grid | 2 | aligned | 0.04 | 18.0 | 5,016 | 177 |
| race_grid | 2 | shifted | 3.36 | 14.7 | 8,498 | 28,548 |
| race_grid | 3 | aligned | 0.01 | 30.0 | 11,860 | 84 |
| race_grid | 3 | shifted | 0.21 | 24.7 | 19,881 | 4,200 |
| race_grid | 4 | aligned | 1.01 | 48.9 | 24,789 | 24,963 |
| race_grid | 4 | shifted | 2.08 | 28.6 | 28,743 | 59,915 |
| race_start | 1 | aligned | 0.41 | 11.7 | 2,022 | 825 |
| race_start | 1 | shifted | 8.02 | 12.1 | 4,489 | 35,987 |
| race_start | 2 | aligned | 0.15 | 16.7 | 4,426 | 664 |
| race_start | 2 | shifted | 3.23 | 15.2 | 8,593 | 27,783 |
| race_start | 3 | aligned | 0.05 | 27.8 | 11,033 | 552 |
| race_start | 3 | shifted | 0.99 | 26.6 | 21,566 | 21,386 |
| race_start | 4 | aligned | 0.01 | 38.0 | 16,968 | 141 |
| race_start | 4 | shifted | 2.34 | 30.0 | 28,858 | 67,577 |
| race_up | 1 | shifted | 6.79 | 10.8 | 3,883 | 26,374 |
| race_up | 2 | aligned | 0.07 | 14.5 | 4,120 | 275 |
| race_up | 2 | shifted | 5.71 | 18.9 | 10,689 | 61,019 |
| race_up | 3 | aligned | 0.02 | 30.0 | 12,464 | 208 |
| race_up | 3 | shifted | 2.20 | 9.4 | 6,159 | 13,550 |
| race_up | 4 | aligned | 0.01 | 35.0 | 9,336 | 78 |
| race_up | 4 | shifted | 2.05 | 29.2 | 28,097 | 57,598 |
| race_drive | 1 | aligned | 0.26 | 11.7 | 2,013 | 516 |
| race_drive | 1 | shifted | 7.99 | 10.9 | 4,019 | 32,097 |
| race_drive | 2 | aligned | 0.13 | 14.2 | 4,128 | 529 |
| race_drive | 2 | shifted | 5.24 | 13.3 | 7,616 | 39,936 |
| race_drive | 3 | aligned | 0.04 | 22.0 | 9,179 | 353 |
| race_drive | 3 | shifted | 0.36 | 24.2 | 20,081 | 7,208 |
| race_drive | 4 | shifted | 2.12 | 28.1 | 27,590 | 58,363 |

## T3 type-0 call outcomes (calls per frame)
| scene | drawn | rows<=0 (nothing) | x off screen | y clipped to nothing | composite (type 1/3) objects | slots active (drawn) | slots in sort list not drawn |
|---|---|---|---|---|---|---|---|
| race_grid | 14.8 | 0.0 | 0.0 | 0.0 | 6.0 | 20.8 | 25.2 |
| race_start | 15.2 | 0.0 | 1.3 | 0.0 | 7.7 | 24.2 | 21.8 |
| race_up | 16.8 | 4.0 | 2.0 | 0.0 | 4.0 | 26.9 | 19.1 |
| race_drive | 16.1 | 1.2 | 1.1 | 0.0 | 6.8 | 25.2 | 20.8 |

## T4 stock kernel cost fit, cycles = a + b * visible rows (type-0 calls of all four scenes)
| cols | x&15 | calls | a | b (cycles/row) | b per column-row |
|---|---|---|---|---|---|
| 1 | aligned | 93 | 421 | 138 | 138 |
| 1 | shifted | 3522 | 497 | 334 | 334 |
| 2 | aligned | 41 | 647 | 235 | 118 |
| 2 | shifted | 1959 | 729 | 524 | 262 |
| 3 | aligned | 12 | -1384 | 456 | 152 |
| 3 | shifted | 441 | -1557 | 853 | 284 |
| 4 | aligned | 145 | -14697 | 807 | 202 |
| 4 | shifted | 988 | 2833 | 881 | 220 |

## T5 kernel variants (type 0 full entries) over all traced calls
| nibble | cols | entry | calls | cycles (M) |
|---|---|---|---|---|
| 7 | 4 | 0x13f6e | 1002 | 27.85 |
| 11 | 2 | 0x130e2 | 2002 | 12.75 |
| 11 | 1 | 0x12a98 | 2918 | 12.60 |
| 13 | 4 | 0x1445c | 155 | 3.74 |
| 7 | 3 | 0x13662 | 161 | 3.27 |
| 7 | 2 | 0x12f60 | 326 | 2.83 |
| 13 | 2 | 0x1327e | 255 | 2.49 |
| 13 | 1 | 0x12bac | 758 | 1.80 |
| 11 | 3 | 0x1384c | 294 | 1.63 |
| 7 | 1 | 0x12994 | 340 | 1.15 |
| 13 | 3 | 0x13a5e | 24 | 0.58 |
| 11 | 4 | 0x141cc | 27 | 0.06 |
