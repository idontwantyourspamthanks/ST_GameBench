; name: pop_ptrfix
; default: yes
; site: $2003e
; orig: 13f900020061 0002478a 33f900020062 00024786 33f900020064 00024788
; note: The IKBD packet handler $1ffc8 / $1fff2 ends a mouse reply ($f7, buttons, x.w, y.w) with three stores of the collected
;       bytes into the pointer variables:
;         02003e move.b $20061.l,$2478a.l / 020048 move.w $20062.l,$24786.l / 020052 move.w $20064.l,$24788.l / 02005c rts
;       Nothing checks them.  When the ACIA loses a byte (it holds one; the interrupt must be served within 1.28 ms) the handler
;       is left in the middle of a packet, the NEXT reply's header $f7 is taken for a data byte, and the five collected bytes are
;       a misframed packet: buttons $f7 and a position such as y = $6e00 or $f708.  The pointer draw $16e20 then addresses the
;       screen with `mulu.w #$a0,y` (016e74) and the first read of the rectangle, 016ec8 `move.w (a4),(a6)+`, bus-errors
;       (Bus Error reading at address $49b500, PC=$16eca on a 1 MB STE; $9fd730 on a Mega STE).  Evidence: work/notes/display.md.
;       The game programs the IKBD for absolute mode with maximum 319 x 199 (`09 01 3f 00 c7` at $1fd86), so a genuine reply has
;       x <= 319, y <= 199 and a buttons byte of four bits.  This patch stores the three values only when they are in range and
;       drops the packet otherwise (the old position and buttons stay).  A genuine packet is stored exactly as before.
;       A misframed packet always carries $f7 in one of its slots (buttons > $0f, x.hi, y.hi or y.lo >= $f7 -> y > 199, or x = $f7 or
;       $1f7 with the rest bounded), so everything that can address outside the screen is dropped; what remains in range
;       is an ordinary position.  Blob $c2800-$c283d.
        org     $2003e
        jmp     $c2800.l

        org     $c2800
pfix:   cmpi.b  #$0f,$20061.l           ; buttons: four bits
        bhi.s   .drop
        cmpi.w  #319,$20062.l           ; x 0..319
        bhi.s   .drop
        cmpi.w  #199,$20064.l           ; y 0..199
        bhi.s   .drop
        move.b  $20061.l,$2478a.l       ; the three original stores
        move.w  $20062.l,$24786.l
        move.w  $20064.l,$24788.l
.drop:  rts                             ; the original falls into the `rts` at $2005c
