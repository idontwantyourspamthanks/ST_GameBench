; Moonshine Racers fixed-rate frame tick (prototype blob), assembled at $b8000. TICK/MAXLAG equ'd by the caller (1/300 s).
CLK     equ     $b8f00          ; long: free-running clock, 1/300 s units
NEXT    equ     $b8f04          ; long: scheduled start of the next pass
PEND    equ     $b8f08          ; byte: 1 = a flip is waiting for its VBL latch

; ---- VBL hook: replaces `addq.b #1,$611b.l` at $d128 (6 bytes -> jsr) --------------------------------------------
vblclk: addq.b  #1,$611b.l      ; the displaced instruction
        clr.b   PEND            ; the flip (if any) is latched by this VBL
        addq.l  #5,CLK.l        ; 60 Hz frame = 5 units of 1/300 s
        btst    #1,$ffff820a.w  ; bit 1 set = 50 Hz
        beq.s   .done
        addq.l  #1,CLK.l        ; 50 Hz frame = 6 units
.done:  rts

; ---- replaces `jsr $d1e4.l` at $7b74 (end of the race pass) -------------------------------------------------------
newsync:
        jsr     $d1ca.l                 ; flip (unchanged routine)
        move.b  #1,PEND.l               ; its latch is now pending
        clr.b   $611a.l                 ; keep the stock meaning of $611a for any other user
.rd:    move.l  CLK.l,d0                ; torn-read safe long read
        cmp.l   CLK.l,d0
        bne.s   .rd
        sub.l   NEXT.l,d0               ; lag = now - next
        bmi.s   .rd                     ; not due yet: sleep until the tick
        cmp.l   #MAXLAG,d0
        bls.s   .ok
        move.l  CLK.l,d0                ; more than MAXLAG behind (pause key, disk, stall): resync, no burst
        cmp.l   CLK.l,d0
        bne.s   .rd
        move.l  d0,NEXT.l
.ok:    add.l   #TICK,NEXT.l
        rts

; ---- replaces `jsr $17c42.l` at $7b0a (first write into the back buffer) -----------------------------------------
pre17c42:
        tst.b   PEND.l
        beq.s   .go                     ; the flipped buffer is already on screen
.w:     tst.b   PEND.l                  ; else wait for the VBL that latches it
        bne.s   .w
.go:    jmp     $17c42.l                ; the raster-table copy stays at $7b7a (stock timing, byte-exact)
