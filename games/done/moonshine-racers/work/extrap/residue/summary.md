# Cloud-edge residue: exact pixel set and when it appears
Producer: `work/int/mx/residue2.py` (Unicorn, exact 68000, on the race-loop ram dumps `work/int/mx/dumps/L<level>.bin`; stock vs the default set + mx with X_TEST=3 = the real extras code, 130 passes per case, inputs `up` and `zig`). Data: `residue.tsv` (main frames, one row per differing pixel), `extras.tsv` (extra frames at those coordinates), `summary.txt`.
Rule: residue = a pixel where a **main frame** differs from the stock main frame of the same pass. Every difference found is in the **sky rows** and in the **buffer that the extra frames had drawn into** (`$78000` in these runs); stock's value is the *older* one (fresh sky or a cleaner silhouette), mx's the *newer* one (a cloud edge left in the buffer).

## Exact set (main frames)
| level | input | buffer | rows | x (all) | stock -> mx colour | main frames with residue | passes |
|---|---|---|---|---|---|---|---|
| 5 | up  | $78000 | 63 | 109, 110 | 14 -> 15 | 44 | 106-192 (every 2nd) |
| 6 | up  | $78000 | 63 | 110 | 14 -> 15 | 44 | 106-192 |
| 6 | zig | $78000 | 63 | 110 | 14 -> 15 | 44 | 106-192 |
| 8 | zig | $78000 | 63 | 109, 110 | 14 -> 15 | 44 | 106-192 |
| 12 | up  | $78000 | 86 | 54, 56-60 | 15 -> 14 ; 7 -> 6 | 1 | 137 |
| 12 | zig | $78000 | 85, 86 | 54, 56-60 | 15 -> 14 ; 7 -> 6 | 1 | 144 |
| 13 | up  | $78000 | 72, 73, 74 | 16-20 (+ | 11 -> 10 ; 15 -> 14 ; 7 -> 6 | 2 | 182, 183 |
| 14 | zig | $78000 | 25-29 | 116 | 15 -> 9 | 20 | 80-99 |
| 0, 5 (zig), 8 (up), 13 (zig), 14 (up) | | | | none | | 0 | |
Palette index = the 4-plane value at that pixel with the game's palettes (`tools/planar.py`), i.e. what the player sees: 14/15 = the sky/cloud greys, 7/6 and 11/10 = mountain ridges, 15->9 a cloud over a ridge.

## Do extra frames show it? (extras.tsv, per level/input)
Every residue pixel lives in the buffer's **carried content**: it changes only when a cloud draw (`de6c`) or cloud erase (`de1c`) covers it. So an extra frame that draws into that buffer keeps it until the next cloud pass over that pixel. Measured (upper bound: the comparison point is stock's last main frame into the same buffer, so a cloud legitimately moving over that pixel also counts):
`L5 up 127, L6 up 118, L6 zig 118, L8 zig 128, L12 up 130, L12 zig 120, L13 up 130, L14 zig 65` extra frames of 283-388 contain at least one residue-coordinate value that differs from that reference.
Answer: **extras show it at least as often as main frames, usually much more often** (e.g. L12: residue in 1 main frame but in 130 extra frames; L13: 2 main frames, 130 extra frames). No case was found where a main frame shows residue that the extras of the same case never show. Consequence for the HUD build: the known set must be checked on *every* frame, not only main frames.

## Use as a regression fixture for the cloud removal / first-frame wipe
1. `python3 work/int/mx/residue2.py 0 5 6 8 12 13 14 --passes 130` and expect `residue pixels 0` for every line (a perfect cloud removal or wipe makes the whole set empty).
2. If only the wipe is done (clouds still drawn), the wipe must cover these rows of **both** buffers: **25-29, 63, 72-74, 85-86** - a wipe of rows 0-64 alone would miss the L12 (85/86) and L13 (72-74) cases, and rows 25-29/63/72-74/85-86 are the only rows that ever carried residue in these 15-level measurements.
3. The wipe must reproduce the **stock** values (column "stock -> mx"), not merely a blank sky: it is the stock history that the main frames are compared against.
