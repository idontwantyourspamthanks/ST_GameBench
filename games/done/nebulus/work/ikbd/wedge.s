; test snippet (NOT part of the patch): hijacks the editor's next poll call ($3853a) to create the stall state while the editor is active:
; mask interrupts, disable GPIP4 (IERB=0 also clears its pending bit), wait for a key byte to arrive in the ACIA, re-enable GPIP4 (the line is already low: no edge), continue with the poll.
        org $b8000
        move.w  sr,-(a7)
        ori.w   #$700,sr
        clr.b   $fffffa09.w
.w:     btst    #0,$fffffc00.w
        beq.s   .w
        move.b  #$40,$fffffa09.w
        move.w  (a7)+,sr
        jmp     $3853a.l
