; name: fal_ym
; default: yes
; falcon: yes
; site: $1bcb8
; orig: 03c88df101888df1
; note: Falcon (master's fal_ym, games/done/powermonger/work/notes/loading.md section 9, regression.md; the same fix for WW1's GAME sample player).  The timer-A sample IRQ ($1bc92..$1bcde) loads
;       a0 = $fa0f and writes the YM with `movep.l d1,-$720f(a0)` = four writes to $ff8800 / 02 / 04 / 06 (the ST decodes $ff8804 / 06 as mirrors of the two registers), then
;       `movep.w d0,-$720f(a0)` = $ff8800 / 02.  A Falcon (Hatari) bus-errors on $ff8804 / $ff8806 [obs: `Bus Error writing at address $ffff8804, PC=$1bcb8`, repeated, work/notes/RESULTS_stage04b.md section 2 item 3].
;       Applied ONLY on a Falcon (class 4, `FALCON` set by core.s `init` from the _MCH cookie): the same four register writes in the same order through $ff8800 / $ff8802 only
;       (two `movep.w`: the high word of d1 = select, data; then the low word, which the original sent to the mirrors).  d1 ends as before (two swaps); the 8 site bytes
;       = `jsr FALYM.l` + `nop`.  ST / STE / TT keep the original instructions (no byte written).
FALYM   equ     $75bd0
        org     $1bcb8
        jsr     FALYM.l
        nop

        org     $75bd0
        swap    d1
        movep.w d1,-$720f(a0)           ; original bytes 3, 2: select, data  ($ff8800 / $ff8802)
        swap    d1
        movep.w d1,-$720f(a0)           ; original bytes 1, 0: they went to the mirrors $ff8804 / $ff8806
        movep.w d0,-$720f(a0)           ; the original's second instruction
        rts
