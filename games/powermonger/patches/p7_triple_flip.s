; name: p7_triple_flip
; default: yes
; stage: 2
; site: $1386c
; orig: 4eb90000187a
; note: P7 triple buffering (work/notes/triple.md), part 2 of 3 (needs p7_triple_wait: data block T, and p7_triple_tail).
;       `jsr $187a` at $1386c = the main loop's flip (the plain flip swaps [$2df78] shown/latest and [$2df7c] drawing, writes $ff8201/03,
;       clears the VBL flag $2df8c).  Here the loop rotates THREE buffers A=$1c700 B=$24400 C=$70000 (C: 32000 B of RAM no code of the
;       game touches, notes section 2): drawing D, latest L, spare X.  After the flip L' = D, D' = X, X' = L.
;       Order of the three steps:
;         1. `jsr $1870`: wait for the VBL handler's flag = one VBL since the previous flip.  A pass lasts several VBLs, so this
;            returns at once in every real scene; it replaces the loop-head wait at $13090 (p7_triple_wait) and keeps at most one
;            flip per VBL (every flipped frame is shown), as the original did.  It also guarantees that the pointer, which the VBL
;            handler restores from the buffer shown before and draws into [$2df78], is out of D' when D' is drawn: D' = X = the
;            buffer shown BEFORE the one the last VBL showed.
;         2. the plain flip (so a debugger breakpoint / A-B capture at $187a still sees every flip) with IN = 1, which the tail hook
;            (p7_triple_tail) turns into OURS = 1;
;         3. [$2df7c] := X (the plain flip put the old L there).
;       D, L must be two different members of {A, B, C}, else the plain flip runs untouched.  X = A+B+C-D-L, so no table is needed
;       and the code works from any (D, L) pair a dialog loop (plain flips) left behind.  Registers as the plain flip leaves them
;       (d0-d1 trashed).
T       equ     $db000
tIN     equ     0
tOURS   equ     2
BUFA    equ     $1c700
BUFB    equ     $24400
BUFC    equ     $70000
        org     $1386c
        jsr     $db100.l

        org     $db100
tflip:  jsr     $1870.l
        move.l  d2,-(a7)
        move.l  $2df7c.l,d0             ; D
        move.l  $2df78.l,d1             ; L
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
        jsr     $187a.l
        move.l  (a7)+,$2df7c.l          ; D' = X
        move.l  (a7)+,d2
        rts
.plain: move.l  (a7)+,d2
        jmp     $187a.l
.in:    cmp.l   #BUFA,d2                ; Z = d2 is one of the three buffers
        beq.s   .y
        cmp.l   #BUFB,d2
        beq.s   .y
        cmp.l   #BUFC,d2
.y:     rts
