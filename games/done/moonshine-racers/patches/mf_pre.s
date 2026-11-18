; name: mf_pre
; default: no
; site: $7b46
; orig: 4eb90000e406
; requires: mf_sync mt_clock mt_pre
; conflicts: mx_pre mx_sync
; data: $B9E00 2752
; doc: Part 2 of 2 of the faster extra frames (mf_sync): saves the object slots before the main frame's object draw as unrolled movem.l bursts (not at all while no extra frame fits).
; note: mx_pre's twin for mf_sync (work/notes/mxfast.md): same site, same data (PREBUF $B9E00, PREV $BA880, NOWANT $B8F50), same behaviour; the copy is 14 x 4 unrolled movem.l pairs written downwards from PREBUF+2688 (mf_sync's prerestore reads it upwards).
; note: The registers are not saved: the next instruction of the pass is `jmp $e406.l` (tc_ord: `movea.l $1008.w,a5 / lea` first), the object stage reads no register of the caller.
PREBUF  equ     $B9E00
PREV    equ     $B9E00+$A80
NOWANT  equ     $B8F50
        org     $7b46
        jsr     $B8300.l

        org     $B8300
mxpre:  tst.b   NOWANT.l
        bne.s   .skip
        lea     $2c68.w,a0
        lea     PREBUF+2688.l,a1
        moveq   #13,d7
.l:     rept    4
        movem.l (a0)+,d0-d6/a2-a6
        movem.l d0-d6/a2-a6,-(a1)
        endr
        dbra    d7,.l
        move.b  #1,PREV.l
.skip:  jmp     $e406.l
