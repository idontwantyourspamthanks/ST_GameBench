; name: pop_keys2
; default: yes
; prog: populous
; site: $2008c
; orig: 13c000037eec
; note: Key recorder for pop_keys (PopUI).  Site $2008c is the last store of the game's ACIA key handler ($1ffc8 -> $1fff2 -> $20066-$20092):
; note: `move.b d0,$37eec.l`, d0 = the scan code of a key press, 0 for a release (a release clears it, so a tap shorter than one pass of the
; note: map loop (0.1-0.3 s) would never be seen by the loop).  The hook performs the displaced store, and for a make code that is in
; note: pop_keys' key table (KT $c7200, scan code / action pairs) appends the action number to the ring Q (KD+12, head KD+10, tail KD+11;
; note: a full ring drops the key).  The interrupt handler has saved d0-d2/a0-a1 ($1ffc8), which is all the hook uses.
; note: Only while the map loop runs: a press counts only if the VBL counter $16d2a is at most WIN VBLs past LASTV (KD+0, stamped by every
; note: pass of pop_keys' hook); otherwise (title, name entry, a long disk access) it is dropped.  Does nothing unless pop_keys' hook is in
; note: place (`$bb7c` starts with `jsr`), so the three patches may be applied in any combination without touching unreserved RAM.
KD      equ     $c8000
KT      equ     $c7200
WIN     equ     150
        org     $2008c
        jsr     $c7300.l

        org     $c7300
kh:     move.b  d0,$37eec.l             ; the displaced store
        tst.b   d0
        beq.s   .r                      ; a release
        cmpi.w  #$4eb9,$0bb7c.l         ; pop_keys installed?
        bne.s   .r
        move.l  $16d2a.l,d1
        sub.l   KD.l,d1
        cmp.l   #WIN,d1
        bhi.s   .r                      ; the map loop is not running
        lea     KT.l,a0
.f:     move.b  (a0)+,d1
        beq.s   .r                      ; not a shortcut key
        cmp.b   d1,d0
        beq.s   .hit
        addq.l  #1,a0
        bra.s   .f
.hit:   move.b  (a0),d1                 ; the action number
        moveq   #0,d2
        move.b  KD+11.l,d2              ; tail
        lea     KD+12.l,a1
        move.b  d1,(a1,d2.w)
        addq.b  #1,d2
        andi.b  #15,d2
        cmp.b   KD+10.l,d2
        beq.s   .r                      ; full: drop
        move.b  d2,KD+11.l
.r:     rts
