; name: p4_walk_save
; default: no
; site: $19f20
; note: item #4 (render.md s8), part 1/3 (with p4_walk_ret_a / p4_walk_ret_b; the three MUST be used together).
; note: sub_019f20 (edge walker) saves d0-d7/a0-a1 (88 cy) and restores them at $1a2c4/$1a610 (92 cy).
; note: Its whole body ($19f20-$1a614, listing in render.md s3) touches only d1-d5, a0, a1 (+ccr): d0, d6, d7, a2, a3
; note: never appear. d1-d5 are dead after the call: both callers reload d0-d5 for the next edge ($19d8c.. /
; note: $19e2a..) and the exits ($1b1bc fill setup, rts) read no data register. a0 (shade table) and a1 (ring table)
; note: are live in the driver, so only a0-a1 are saved. Saves 128 cy per edge (172 edges/frame walk).
        org     $19f20
        movem.l a0-a1,-(a7)
