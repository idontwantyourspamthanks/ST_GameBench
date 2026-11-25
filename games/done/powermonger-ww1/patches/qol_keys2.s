; name: qol_keys2
; default: yes
; site: $f30
; orig: 13c00001d2b0
; note: the interrupt half of qol_keys (see there; harmless without it: it only writes PEND bytes).  $f30 is the make-code path of the game's ACIA keyboard handler
;       ($ef6, `st.b (a0,d0.w)` just stored the key in the table $2ec8c, d0 = the scan code, 0 for a break): `move.b d0,$1d2b0` (the game's "last key" byte) becomes
;       `jsr KH`; KH does that same move, and for a make code sets PEND[scancode] = 1 (+ 2 when Shift is down, $2edaa) in qol_keys' data block.  qol_keys consumes
;       PEND once per pass, so a tap shorter than a pass is not lost.  A press is recorded only while the map loop runs (LASTV, see qol_keys).  The handler saved the
;       registers it uses (master $18be -> WW1 $ee4..): d0, d1, a0 are free here (the displaced code after the site is `move.b d0,$2eda9 ; movea.l (a7)+,a0 ; rts`).
PEND    equ     $73044
ANY     equ     $73042
LASTV   equ     $730c4                  ; qol_keys: D + $c4
DET_REQ equ     $75302                  ; qol_detail: F5 / Alt+D request byte
TH      equ     $72f80                  ; qol_type: FIFO head
TT      equ     $72f82                  ; qol_type: FIFO tail
RING    equ     $72f84                  ; qol_type: 64-byte ring buffer
WIN     equ     150                     ; = qol_keys.s

        org     $f30
        jsr     $72e50.l

        org     $72e50
kh:     move.b  d0,$1d2b0.l             ; the displaced instruction
        tst.b   d0
        beq.w   .r                      ; a break code (d0 was cleared)
        tst.b   $d424.l                 ; typing into a text box (name prompt, save name)?
        beq.s   .map
        move.w  TT.l,d1                 ; push (scancode.b, shift.b) into TFIFO
        move.w  d1,a0
        addq.w  #2,d1
        andi.w  #62,d1
        cmp.w   TH.l,d1
        beq.s   .r                      ; FIFO full
        move.w  d1,TT.l
        move.w  a0,d1
        lea     RING.l,a0
        move.b  d0,0(a0,d1.w)
        tst.w   $2edaa.l
        sne     1(a0,d1.w)
        rts
.map:   move.l  $71b7c.l,d1             ; VBL count now
        sub.l   LASTV.l,d1              ; VBLs since the last pass hook (LASTV = 0 before the first pass: a huge difference)
        cmp.l   #WIN,d1
        bhi.s   .r                      ; the loop is not running: not a shortcut
        cmpi.b  #$3f,d0                 ; F5: cycle detail level
        beq.s   .det
        cmpi.b  #$20,d0                 ; D key?
        bne.s   .norm
        tst.b   $2ec8c+$38.l            ; Alt held?
        beq.s   .norm
.det:   st.b    DET_REQ.l               ; F5 / Alt+D: cycle detail level (do not fire D = Drop Food)
        rts
.norm:  lea     PEND.l,a0
        moveq   #1,d1
        tst.w   $2edaa.l                ; Shift down?
        beq.s   .s
        moveq   #3,d1
.s:     move.b  d1,(a0,d0.w)
        move.w  #1,ANY.l                ; after PEND: the pass hook scans only when this is set
.r:     rts
