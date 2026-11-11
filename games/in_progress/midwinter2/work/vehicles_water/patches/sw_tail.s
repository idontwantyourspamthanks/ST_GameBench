; name: sw_tail
; default: no
; site: $33d4c
; orig: 3028000208000000
; note: ANALYST SCRATCH: sub_033bde type tail. bit6-only types (flags & $41 = $40: Minisub, Submarine, Frogman) run at $33d70 the
;       non-idempotent clamp of $764c against the sea floor ($66e2 = $764c-$66e4 < $32 -> $33e1a reset; clamp [$34936,$34938+$1e]).
;       On a masked type's PH 1-4 it is skipped (jump to the tail probe $33e30, which sw_probe2 also skips), so the clamp acts once on the
;       group sum on PH 5 with the group's bounds, as the unpatched tick.
D       equ     $b42e0
        org     $33d4c
        jsr     $b4fc0.l
        nop

        org     $b4fc0
        move.w  $2(a0),d0               ; the replaced instructions
        tst.w   D+8.l                   ; SUB
        beq.s   .orig
        cmpi.w  #5,D+6.l                ; PH
        beq.s   .orig
        btst    #6,d0
        beq.s   .orig
        btst    #0,d0
        bne.s   .orig
        addq.l  #4,a7
        jmp     $33e30.l
.orig:  btst    #0,d0
        rts
