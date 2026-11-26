; name: mt_clock
; default: yes
; site: $d128
; orig: 52390000611b
; data: $B8F00 4
; data: $B8F08 4
; doc: Fixed real-time game tick, part 1 of 3 (needs mt_pre and a pacer: mx_sync (default) or mt_sync): a 1/300 s clock advanced by the VBL handler (+6 at 50 Hz, +5 at 60 Hz).
; note: Moonshine Racers fixed tick (work/notes/tick.md, design work/notes/timing.md section 3).  Part 1 of 3: mt_clock + mt_pre + a pacer (mx_pre + mx_sync, or mt_sync) must be installed together.
; note: Site: $d128 `addq.b #1,$611b.l` in the VBL ISR ($d11e) -> `jsr $B8000.l`; the blob replays the addq first, clears the flip-pending byte PEND ($B8F08: the new
; note: video base is latched by this VBL) and adds 5 (60 Hz) or 6 (50 Hz: bit 1 of the sync-mode register $ffff820a, present on ST/STE/TT/Falcon) to the long CLK ($B8F00).
; note: Only memory and CCR are touched (the ISR's registers are not disturbed; the CCR is not live across the displaced addq).
CLK     equ     $B8F00
PEND    equ     $B8F08
        org     $d128
        jsr     $B8000.l

        org     $B8000
vblclk: addq.b  #1,$611b.l      ; the displaced instruction
        clr.b   PEND.l          ; a pending flip is latched by this VBL
        addq.l  #5,CLK.l        ; 60 Hz frame = 5 units of 1/300 s
        btst    #1,$ffff820a.w  ; bit 1 set = 50 Hz
        beq.s   .done
        addq.l  #1,CLK.l        ; 50 Hz frame = 6 units
.done:  rts
