; name: mx_pre
; default: no
; site: $7b46
; orig: 4eb90000e406
; requires: mx_sync mt_clock mt_pre
; data: $B9E00 2752
; doc: Part 2 of 2 of the extra frames (mx_sync): saves the object slots before the main frame's object draw (not at all while no extra frame fits).
; note: Needs mx_sync (and mt_clock, mt_pre).  Site $7b46 `jsr $e406.l` (object draw of the race pass) -> `jsr $B8300.l`: unless mx_sync reported that no extra frame fitted into the last
; note: tick (NOWANT, $B8F50: an 8 MHz machine pays nothing), the blob copies the 48 object slots $2c68..$36e7 (2688 bytes) to PREBUF ($B9E00) and tail-jumps to $e406.
; note: The stages that follow the draw ($18888, $18c86, $18f0e: collision response, debris) change the slots, so the state the draw saw exists only here.  The extra frames start from this copy.
; note: PREV ($B9E00+2688) = 1 tells mx_sync that PREBUF is valid for this tick.
PREBUF  equ     $B9E00
PREV    equ     $B9E00+$A80
NOWANT  equ     $B8F50
        org     $7b46
        jsr     $B8300.l

        org     $B8300
mxpre:  tst.b   NOWANT.l
        bne.s   .skip
        movem.l d0-d7/a0-a6,-(a7)
        lea     $2c68.w,a0
        lea     PREBUF.l,a1
        moveq   #55,d7                  ; 56 * 48 bytes
.l:     movem.l (a0)+,d0-d6/a2-a6
        movem.l d0-d6/a2-a6,(a1)
        lea     48(a1),a1
        dbra    d7,.l
        move.b  #1,PREV.l
        movem.l (a7)+,d0-d7/a0-a6
.skip:  jmp     $e406.l
