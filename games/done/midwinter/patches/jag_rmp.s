; name: jag_rmp
; default: yes
; site: $6696
; orig: 14390002c32e
; note: Jaguar pad support, part 4 of 4 (see jag_vbl; work/notes/jagpad.md).  J-mode fire remap of the input funnel: `tst.w $2c178 / beq` then
;       `move.b $2c32e.l,d2 / cmp.b #$f9,d2 / bne` -> `$24fba = 2` (left button): the IKBD reports a joystick-1 fire as the mouse header
;       $f9, which the game turns into the LEFT button.  With the pad fire held (PADBTN = 1) the byte is $f9 regardless of $2c32e, so the pad
;       fire gives exactly that remap (and it survives the VBLs where $65c0 rewrote $2c32e).
        org     $6696
        jsr     $b6c20.l

        org     $b6c20
        move.b  $2c32e.l,d2             ; displaced
        tst.b   $b6bf2.l                ; PADBTN (jag_vbl)
        beq.s   .r
        move.b  #$f9,d2
.r:     rts
