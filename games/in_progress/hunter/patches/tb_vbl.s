; name: tb_vbl
; default: no
; site: $c600
; orig: 4a6d00ea6f04
; requires: tb_flip tb_frame
; note: Triple buffering, part 3 of 3 (needs tb_flip: the state block TBVBL/TBON).  The VBL handler's palette-fade
;       tick `tst.w $ea(a5) / ble.s` becomes `jsr tb_vbl`, which counts VBLs (tb_flip's >=1-VBL rule between flips needs
;       a per-VBL tick that does not depend on the 3D loop being active or on hn_hz's 50/60 Hz world gate) and then runs
;       the original two instructions unchanged.  Runs once per VBL in every mode; ~40 cycles (0.025 % of the CPU).
TBB     equ     $8c1b2                  ; state block (tb_flip.s): +0 VBL counter, +2 VBL at the last flip, +4 mode
TBVBL   equ     TBB+0
TBCODE  equ     $8c2f0

        org     $c600
        jsr     TBCODE.l

        org     $8c2f0
tb_vbl: addq.w  #1,TBVBL.l
        tst.w   $ea(a5)                 ; the displaced `tst.w $ea(a5)`
        ble.s   .out                    ; the displaced `ble.s $c60a`
        subq.w  #1,$ea(a5)              ; the displaced `subq.w #1,$ea(a5)`
.out:   rts
