; name: pop2_save_b
; default: no
; site: $20e
; orig: 30804ef90002cc9c
; note: Part B of the in-game save/load fix (see pop2_save_a): PP's hook of the file-by-number function $2cc98 (`jmp $206`; $206 saves the
; note: registers, `lea $148(pc),a0`, `move.w d0,(a0)` = the file number into the stub's `move.w #n,d0`, `jmp $2cc9c`).  The displaced
; note: `move.w d0,(a0)` is replayed and the flag that tells the stub entry "the next call is this function's" is set.
FLAG    equ     PB+$2f0
HOOK    equ     PB+$340

        org     $20e
        jmp     HOOK.l
        nop

        org     PB+$340
        move.w  d0,(a0)
        st.b    FLAG.l
        jmp     $2cc9c.l
