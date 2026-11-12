; name: pop_tick_cmd
; default: no
; site: $0bbf8
; orig: 4267 4eb9 0001e750
; note: Fixed-rate world tick, part 5 of 6 (needs pop_tick and pop_tick_flip; work/notes/timing.md).  End of a pass: `clr.w -(a7)` / `jsr $1e750` (executes both players' queued commands -
;       three bytes in the player record $21e4a + $2e * n, run through the table $21652: raise/lower land, magnet, earthquake, volcano, swamp, behaviour, flood, Armageddon, pause -
;       and clears them), then $bc00 `addq.l #2,a7`, $bc02 `move.w #1,d0` / `bne.w $b632`.  A render-only pass (kind R, flag RON: ahead of real time) does not execute: the player acts
;       once per TURN whatever the speed of the machine (a command is written only by a UI pass that takes a click, and pop_tick_flip hides fresh clicks from the UI of render-only
;       passes, so the commands come from turn passes).  It puts back the fresh click latches that pop_tick_flip hid (FLAGS bit 0 left $3d566, bit 1 right $3c514: written 0 again; the UI pass left
;       them at 1, or at 0 where the VBL routine latched a new press meanwhile) with interrupts masked, and goes on at $bc02.  Any other pass: the displaced instructions, then $bc00.
D       equ     $c6000
oRON    equ     16
oFLAGS  equ     20
        org     $0bbf8
        jmp     $c5500.l
        nop

        org     $c5500
        tst.w   D+oRON.l
        bne.s   .r
        clr.w   -(a7)
        jsr     $1e750.l
        jmp     $0bc00.l
.r:     move.w  sr,-(a7)
        ori.w   #$700,sr
        btst    #0,D+oFLAGS+1.l
        beq.s   .n1
        clr.w   $3d566.l                ; the fresh left click is still waiting
.n1:    btst    #1,D+oFLAGS+1.l
        beq.s   .n2
        clr.w   $3c514.l
.n2:    clr.w   D+oFLAGS.l
        move.w  (a7)+,sr
        jmp     $0bc02.l
