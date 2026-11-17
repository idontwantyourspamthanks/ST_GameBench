; name: ta_erase
; default: no
; site: $1209c
; orig: 4eb90001242c
; data: $BEF00 16
; requires: hd_stage
; doc: Speech, part 1: the message-box restore (two passes of ~35 k cycles per message) as a straight long fill (~11.6 k each); pixel-identical, also invalidates the face shadows (ta_face).
; note: Tighten wave A (work/notes/tighten_a.md).  Site $1209c: `jsr $1242c.l` inside the ticker's box restore $12086 (x 112, y 16, 192 px wide, 49 rows, colour 15 = all four planes set).
; note: The stock kernel fills with `movem.w d1-d4,(a0)` per 16 pixels (and writes the dead occupancy map $6f000); the blob writes the same 96 bytes per row with two `movem.l` of twelve registers.
; note: `$100c` (kernel scratch, masked by the state gates) gets the value the stock kernel leaves there (row 16, byte 56 = 2616).  Registers: the stock call clobbers d0-d5 d7 a0 a1 a3 a4 and the callers reload everything they use.
; note: Data $BEF00: FV0 / FV1 = what the face shadow of the buffer $70000 / $78000 holds (word, $ffff = nothing drawn); the erase wipes the face, so it writes $ffff for the buffer it erases.  The words are read by ta_face / ta_facestat.
FV0     equ     $BEF00
FV1     equ     $BEF02
        org     $1209c
        jsr     $BE000.l

        org     $BE000
erase:  move.l  a5,d0
        btst    #15,d0                  ; $78000?
        bne.s   .b1
        move.w  #$ffff,FV0.l
        bra.s   .go
.b1:    move.w  #$ffff,FV1.l
.go:    lea     2616(a5),a0             ; row 16, byte 56 (x 112)
        lea     49*160(a0),a6           ; end
        moveq   #-1,d0
        move.l  d0,d1
        move.l  d0,d2
        move.l  d0,d3
        move.l  d0,d4
        move.l  d0,d5
        move.l  d0,d6
        move.l  d0,d7
        movea.l d0,a1
        movea.l d0,a2
        movea.l d0,a3
        movea.l d0,a4
.row:   movem.l d0-d7/a1-a4,(a0)
        movem.l d0-d7/a1-a4,48(a0)
        lea     160(a0),a0
        cmpa.l  a0,a6
        bne.s   .row
        move.w  #2616,$100c.w
        rts
