; name: p7_triple_flip
; default: yes
; site: $145e2
; orig: 4eb900000e0e
; note: triple buffering (master p7_triple_flip / triple.md), part 2 of 3 (needs p7_triple_wait: data block T, and p7_triple_tail).  Re-sited: master $1386c -> WW1 $145e2.
;       `jsr $e0e` at $145e2 = the main loop's flip (the plain flip swaps [$2ed98] shown/latest and [$2ed9c] drawing, writes the video base, clears the VBL flag $2edac).  Here the loop rotates THREE buffers
;       A=$1d500 B=$25200 C=$b0000: drawing D, latest L, spare X.  After the flip L' = D, D' = X, X' = L.  Order of the three steps:
;         1. `jsr $e04`: wait for the VBL handler's flag = one VBL since the previous flip.  A pass lasts several VBLs, so this returns at once in every real scene; it replaces the loop-head wait at
;            $13e04 (p7_triple_wait) and keeps at most one flip per VBL (every flipped frame is shown).  It also guarantees that the pointer, which the VBL handler restores from the buffer shown before and
;            draws into [$2ed98], is out of D' when D' is drawn: D' = X = the buffer shown BEFORE the one the last VBL showed.
;         2. the plain flip (so a debugger breakpoint / A-B capture at $e0e still sees every flip) with IN = 1, which the tail hook (p7_triple_tail) turns into OURS = 1;
;         3. [$2ed9c] := X (the plain flip put the old L there).
;       D, L must be two different members of {A, B, C}, else the plain flip runs untouched.  X = A+B+C-D-L, so no table is needed and the code works from any (D, L) pair a dialog loop (plain flips)
;       left behind.  Registers as the plain flip leaves them (d0-d1 trashed).
T       equ     $77380
tIN     equ     0
tOURS   equ     2
BUFA    equ     $1d500
BUFB    equ     $25200
BUFC    equ     $b0000
        org     $145e2
        jsr     $77240.l

        org     $77240
tflip:  jsr     $e04.l
        move.l  d2,-(a7)
        move.l  $2ed9c.l,d0             ; D
        move.l  $2ed98.l,d1             ; L
        cmp.l   d0,d1
        beq.s   .plain
        move.l  d0,d2
        bsr.s   .in
        bne.s   .plain
        move.l  d1,d2
        bsr.s   .in
        bne.s   .plain
        move.l  #BUFA+BUFB+BUFC,d2
        sub.l   d0,d2
        sub.l   d1,d2                   ; X
        move.l  d2,-(a7)
        move.w  #1,T+tIN.l
        jsr     $e0e.l
        move.l  (a7)+,$2ed9c.l          ; D' = X
        move.l  (a7)+,d2
        rts
.plain: move.l  (a7)+,d2
        jmp     $e0e.l
.in:    cmp.l   #BUFA,d2                ; Z = d2 is one of the three buffers
        beq.s   .y
        cmp.l   #BUFB,d2
        beq.s   .y
        cmp.l   #BUFC,d2
.y:     rts
