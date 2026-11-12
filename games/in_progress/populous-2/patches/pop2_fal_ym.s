; name: pop2_fal_ym
; default: no
; site: $2a938
; orig: 21fc0002aa4e0134
; note: Falcon only (hwscan.py found it; Populous's pop_fal_ym is the same fix).  The game's sample interrupt (MFP timer A, handler $2aa4e..$2aaa0,
; note: installed by $2a938 and $2a9aa) writes the three YM volumes with `lea.l $fa0f.w,a0 / movep.l d1,-$720f(a0) / movep.w d0,-$720f(a0)` at
; note: $2aa74: a0 + -$720f = $ff8800, so the movep.l writes $ff8800 / $ff8802 / $ff8804 / $ff8806.  A Falcon bus-errors on the mirror pair.
; note: pop2patch has no machine gate (the core applies every site on every machine), so the gate is a run-time one that costs the other machines
; note: nothing: the site is the one-off install of the timer-A vector at game start (`move.l #$2aa4e,$134.w`, 8 B -> `jsr` + nop).  The blob
; note: does that instruction, then reads the _MCH cookie ($5a0, high word 3 = Falcon, as Powermonger's fal_ym does).  Only on a Falcon it rewrites
; note: the 8 bytes at $2aa74 (both movep, after checking they are the original bytes) into `jsr hook.l / nop` and empties the 68030 caches; on every other machine it
; note: returns and the handler is untouched, so ST / STE / Mega STE / TT execute the original bytes with the original timing.
; note: hook = the same register writes in the same order through $ff8800 / $ff8802 only: swap d1, movep.w (bytes 3,2), swap d1, movep.w (bytes 1,0),
; note: then the original movep.w d0.  d1, d0 and a0 end as before.  Costs about 70 cycles more per interrupt on the Falcon [INFERENCE: not measured].
; note: Blob range: PB+$1000..$10ff (free: nothing else owns it).
SITE    equ     $2aa74
        org     $2a938
        jsr     PB+$1000
        nop

        org     PB+$1000
inst:   move.l  #$2aa4e,$134.w          ; the displaced instruction
        movem.l d0-d1/a0,-(a7)
        movea.l $5a0.w,a0               ; _p_cookies
        move.l  a0,d0
        beq.s   .x
.c:     move.l  (a0)+,d0                ; cookie id, 0 = end of the jar
        beq.s   .x
        move.l  (a0)+,d1                ; value
        cmpi.l  #'_MCH',d0
        bne.s   .c
        swap    d1
        cmpi.w  #3,d1                   ; high word 3 = Falcon
        bne.s   .x
        lea     SITE.l,a0
        cmpi.l  #$03c88df1,(a0)+        ; movep.l d1,-$720f(a0)
        bne.s   .x
        cmpi.l  #$01888df1,(a0)         ; movep.w d0,-$720f(a0)
        bne.s   .x
        lea     SITE.l,a0
        move.w  #$4eb9,(a0)+            ; jsr hook.l
        move.l  #PB+$1080,(a0)+
        move.w  #$4e71,(a0)             ; nop
        dc.w    $4e7a,$0002             ; movec cacr,d0 (Falcon = 68030)
        ori.l   #$0808,d0               ; CI + CD: clear the instruction and the data cache
        dc.w    $4e7b,$0002             ; movec d0,cacr
.x:     movem.l (a7)+,d0-d1/a0
        rts

        org     PB+$1080
hook:   swap    d1
        movep.w d1,-$720f(a0)           ; $ff8800, $ff8802 = bytes 3, 2 of d1
        swap    d1
        movep.w d1,-$720f(a0)           ; bytes 1, 0 (the original wrote them to the mirror $ff8804 / $ff8806)
        movep.w d0,-$720f(a0)           ; the original's next instruction (its 4 bytes were replaced too)
        rts
