; name: ta_facestat
; default: no
; site: $f994
; orig: 41f90001b076
; requires: hd_stage ta_erase ta_init
; conflicts: ta_face
; doc: Speech, part 2 (VISIBLE, alternative to ta_face): the talking face is drawn ONCE per message and buffer with the mouth frame of the message's first pass (no mouth animation).
; note: Tighten wave A (work/notes/tighten_a.md).  Same site and entry conditions as ta_face (d0 = sprite index at $f994).  The message pointer word $11a8 identifies the message: when it changes, the frame d0 of that pass becomes the message's frame (GFR $BEF06, key GKEY $BEF04);
; note: each buffer (FV0 / FV1 = $BEF00 / $BEF02, invalidated by the box restore and the race init) draws that frame once per message, then returns as the stock routine does at $f9f8.  Pixel difference to stock: the mouth/eye pixels of the face (x 272-303, y 17-64) no longer change while a message is typed.
FV0     equ     $BEF00
FV1     equ     $BEF02
GKEY    equ     $BEF04
GFR     equ     $BEF06
        org     $f994
        jmp     $BE180.l

        org     $BE180
facest: move.w  $11a8.w,d1
        cmp.w   GKEY.l,d1
        beq.s   .k
        move.w  d1,GKEY.l
        move.w  d0,GFR.l
.k:     lea     FV0.l,a0
        cmpa.l  #$78000,a5
        bne.s   .b0
        addq.l  #2,a0
.b0:    cmp.w   (a0),d1
        beq.s   .skip
        move.w  d1,(a0)
        move.w  GFR.l,d0
        lea     $1b076.l,a0
        jmp     $f99a.l
.skip:  rts
