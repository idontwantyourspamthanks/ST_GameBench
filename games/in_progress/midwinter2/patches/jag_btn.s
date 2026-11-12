; name: jag_btn
; default: no
; site: $26bea
; orig: 141002420003
; note: Atari Jaguar pad, part 3 of 3 (work/notes/jagpad.md; poll in jag_poll).  J-mode part of the joystick re-read $26b58:
;       `move.b (a0),d2 / andi.w #3,d2` (a0 = $75a2, the IKBD mouse header: bit0 = right button = what a joystick-1 fire reports) is followed by
;       `move.w d2,$6872.w`, the select / fire event ($1ab70 in J mode). The blob replays both instructions and ORs PADBTN ($b9ee2, bit0 = pad B,
;       written once per VBL by jag_poll, zero without it) into d2. The pad's A and C do not come through here: they make the `,` / `.` keys, which
;       the next instructions ($26bf4) turn into the left / right "mouse buttons" ($6fbe: nose down / up, dive / climb, menu clicks).
PADBTN  equ     $b9ee2
        org     $26bea
        jsr     $b9e20.l

        org     $b9e20
        move.b  (a0),d2                 ; displaced
        andi.w  #3,d2
        or.b    PADBTN.l,d2
        rts
