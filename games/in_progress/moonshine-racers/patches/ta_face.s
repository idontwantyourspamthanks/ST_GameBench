; name: ta_face
; default: yes
; site: $f994
; orig: 41f90001b076
; requires: hd_stage ta_erase ta_init
; conflicts: ta_facestat
; doc: Speech, part 2: the talking face is drawn only when the picture it would draw differs from the one the buffer already shows (pixel-identical).
; note: Tighten wave A (work/notes/tighten_a.md).  Site $f994 = `lea.l $1b076.l,a0` in the face routine $f90c, reached with d0 = the sprite index of this pass (the mouth frame; during a message that is typed the index follows the face RNG,
; note: while it is held it is constant).  The state machine up to here (face sequence $10ec-$10f9, RNG $dafc) runs exactly as in stock.  The blob compares d0 with FV0 / FV1 (the index last drawn into the buffer $70000 / $78000, ta_erase's data):
; note: equal = the masked draw would repaint the same pixels (a masked sprite draw is idempotent), so it returns as the stock routine does at $f9f8; different = store, replay the displaced lea and continue at $f99a.
; note: FV words are invalidated by the box restore (ta_erase) and by the race init (ta_init), the only two writers of that area apart from the face itself.  Also used by the extra frames (mx_sync calls $f90c).
FV0     equ     $BEF00
FV1     equ     $BEF02
        org     $f994
        jmp     $BE100.l

        org     $BE100
face:   lea     FV0.l,a0
        cmpa.l  #$78000,a5
        bne.s   .b0
        addq.l  #2,a0                   ; FV1
.b0:    cmp.w   (a0),d0
        beq.s   .same
        move.w  d0,(a0)
        lea     $1b076.l,a0             ; the displaced instruction
        jmp     $f99a.l
.same:  rts
