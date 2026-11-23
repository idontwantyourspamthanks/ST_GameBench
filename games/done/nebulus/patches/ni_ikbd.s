; Nebulus input: IKBD/ACIA resync (NebInputStall).  Blob at IK = $7726c (the 148-byte gap between the editor's tables (end $7726c) and CODE2 ($77300);
; verified zero at stage 2 like every other blob).  Two sites, both in stock game code that Gamex / the other patches do not touch.
;
; THE BUG (stock Nebulus + Gamex, reproduced on the unpatched NEBORIG): START.TOS runs `move.w #$2700,sr` ($35c) and then depacks the game, so the TOS keyboard
; interrupt does not run for ~1.3 s (66 VBL) until the game's init sub_0383f6 installs its own ACIA handler ($384fc) and lets interrupts in ($38486).  Any byte the
; IKBD sends in that window (a key make/break, a joystick packet, a mouse packet) sits unread in the ACIA data register: the ACIA keeps its IRQ line LOW, the
; MFP detects interrupts by EDGE, and sub_0383f6 first clears IERB/IPRB ($fa09/$fa0d/...) and only then re-enables GPIP4, so the pending interrupt is lost and
; the line never goes high again: the game never sees another key or joystick byte for the rest of the run (F9/F10/D, fire, everything).  The handler also
; reads the data register only once, so an overrun (OVRN) left by a second byte can keep the line low as well.
;
;   drain  (site $38486, 8 B: `move.w #$2300,sr` + `bsr.w $33e84`)  runs at SR $2700, after the MFP is armed: reads the ACIA data register while the status shows
;          RDRF or OVRN (bounded), so the line is high when interrupts are let in; then the original `move.w #$2300,sr` and a tail jump to $33e84 (= bsr + rts).
;   wd     (site $3853a, 8 B: `movem.l d0-d1/a0,-(a7)` + `move.b $38498(pc),d0`, the entry of the game's poll sub_03853a, called once per title/game loop and
;          from the editor's loops)  watchdog: if the ACIA status shows RDRF or OVRN in MAIN context (a byte that should have caused the interrupt long ago),
;          run the real handler $384fc once with interrupts masked through a fake exception frame (it reads the byte, goes through the Gamex hook, the latch
;          hooks and `bclr #6,$fa11` = clears a stuck in-service bit too, then `rte`s back).  Self-heals any stall (also a stuck in-service bit or a lost edge)
;          within one poll (<= 2 VBL = 40 ms); in normal play the status bits are clear and the cost is one status read per poll.
IK      equ $7726c
        org IK
drain:                              ; site $38486
        move.l  d0,-(a7)
        moveq   #15,d0              ; bounded: a stuck-high status can never hang the boot
.l:     btst    #0,$fffffc00.w      ; RDRF
        bne.s   .r
        btst    #5,$fffffc00.w      ; OVRN (cleared by status read + data read)
        beq.s   .d
.r:     tst.b   $fffffc02.w         ; data read
        dbra    d0,.l
.d:     move.l  (a7)+,d0
        move.w  #$2300,sr
        jmp     $33e84.l            ; was bsr.w $33e84 / rts

wd:                                 ; site $3853a
        movem.l d0-d1/a0,-(a7)
        move.b  $fffffc00.w,d0
        andi.b  #$21,d0             ; RDRF | OVRN
        beq.s   .ok
        bsr.s   heal
.ok:    move.b  $38498.l,d0         ; was move.b $38498(pc),d0
        jmp     $38542.l
heal:   move.w  sr,-(a7)
        ori.w   #$700,sr
        pea     .r(pc)              ; fake exception frame: PC, then SR; the handler's rte lands at .r
        move.w  sr,-(a7)
        jmp     $384fc.l
.r:     move.w  (a7)+,sr
        rts
