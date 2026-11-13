; name: test_mlogd
; default: no
; hdonly: yes
; site: $a65c
; orig: 47fa00bc08ad000001ce
; note: Measurement only (tools/huntmouse.py): logs the pointer position the game DRAWS each VBL.  Entry = the first two instructions of the pointer
; note: redraw $a65c (`lea.l $a71a(pc),a3 / bclr.b #0,$1ce(a5)`), redone here with the flags of the bclr left for the `beq.b` that follows.
; note: Log at $b8200 (HD builds: $B8200-$BFFFF is free): +0 write pointer.l (0 = not started), +4 VBL count.l, entries of 8 bytes from +16:
; note: word VBL count, word type (0 = position), word x, word y.  Not in the release set.
        org     $a65c
        jsr     $8dc00.l
        nop
        nop

        org     $8dc00
mlogd:  movem.l d0/a0-a1,-(sp)
        lea     $b8200.l,a0
        move.l  (a0),d0
        bne.s   .ok
        lea     16(a0),a1
        move.l  a1,d0
        move.l  d0,(a0)
.ok:    addq.l  #1,4(a0)
        cmp.l   #$bffe0,d0
        bcc.s   .skip
        movea.l d0,a1
        move.w  6(a0),(a1)+
        clr.w   (a1)+
        move.w  $d8(a5),(a1)+
        move.w  $da(a5),(a1)+
        move.l  a1,(a0)
.skip:  movem.l (sp)+,d0/a0-a1
        lea     $a71a.l,a3
        bclr.b  #0,$1ce(a5)
        rts
