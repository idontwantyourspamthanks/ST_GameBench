; Nebulus gameplay patch np_shot (NebShotMiss): the player's shot hits a creature whose centre is ABOVE the shot's height.  DEFAULT NO, changes original behaviour.
; In-place, 4 bytes, no RAM blob, no new code.
;
; sub_03b7d6 (overlap test, called with a1 = the box being tested, a0 walks the 4 creature slots; the shot is slot 4 = $3394c, the player's hit box slot 5 = $3394e):
;   x:  d0 = (a1.x - a0.x) & $7f, must be -3..+2 (angle units)
;   y:  d0 = (a1.y - a0.y) & $3ff, must be 0..7 or $3f9..$3ff   (i.e. -7..+7)
;   $3b860  addi.w #7,d0            ; row index = dy+7 for the shape table ($3b7c6 for the shot, $3b7b6 for creature-vs-creature), 16 rows, 1 byte each
;   $3b884  adda.w d0,a2 / move.b (a2),d0 / addq.w #1,d1 / lsr.b d1,d0 / bcc no_hit     (d1 = x diff + 3 = the bit to look at)
; For a NEGATIVE dy (the shot is lower than the creature's centre) d0 was $3f9..$3ff, so the "+7" gives $400..$406 and the table is read $400 bytes too far:
; the mask comes from the game's own code ($3bbc6..$3bbcc for the shot) instead of the shape table.  Measured stock hit box of the shot (X = hit) for dy = -7..+5:
;   dy  -7 -6 -5 -4 -3 -2 -1  0 ..  3  4  5      x diff -3..+2:  -7 .X.XXX | -6 ...XX. | -5 ....XX | -4 X..XXX | -3 ...... | -2 XX.... | -1 X..XXX | 0..3 .XXXXX | 4,5 ..XXX.
;   intended (the table)                                          -7 ..XXX. | -6..3 .XXXXX | 4,5 ..XXX.
; A hopping ball (creature kind 1, y rises up to 6 units above the frog's shot height) is therefore missed by shots in about one fifth of the phases ("bullet flies,
; hits the enemy and nothing happens"); creatures that stay at the shot's height (walkers, dy >= 0) were never affected.
;
; Fix (shot only; creature-vs-creature and everything else keep the stock result, bug included):
;   $3b87a  66 00 00 08        bne.w $3b884            ->  66 08 48 80     bne.b $3b884 ; ext.w d0
;   i.e. the branch that skips `lea $3b7c6,a2` for every box but the shot becomes short (2 B) and the freed word is `ext.w d0` on the shot path: the low byte of
;   d0 ($00..$0e for dy >= 0, $00..$06 after the +$400 for dy < 0) is sign-extended, which removes the $400.  d0 is dead after the table read.
        org $3b874
        cmpa.l  #$3394c,a1         ; unchanged  (b3fc 0003394c)
        bne.b   .skip              ; 6608
        ext.w   d0                 ; 4880      NEW: row index = dy+7 again (0..14)
        lea     $3b7c6.l,a2        ; unchanged  (45f9 0003b7c6)
.skip:  adda.w  d0,a2              ; $3b884
