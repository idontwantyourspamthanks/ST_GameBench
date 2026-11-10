; name: sync_blip
; default: no
; site: $800
; orig: 4ff90002d446
; phase: boot
; note: Hatari-only cosmetic fix, harmless on hardware.  PP's intro-picture viewer (RUNME.TOS, the overscan FLAMES / MIDWINTER picture,
; note: runs before the game) opens the top and bottom border at 50 Hz and then restores the sync mode TOS booted with.  Where that is
; note: 60 Hz (TOS 2.06 / 3.06 as Hatari boots them), Hatari's 60 Hz frame has fewer border lines than its 50 Hz window and keeps
; note: the last overscan picture rows there: a coloured stripe band under the picture (x 107-738, the last 17 border lines) on every
; note: screen of the session (games/midwinter2/work/notes/logo_stripes.md; the same with the unpatched PP files).  Showing a few real 50 Hz frames
; note: with the black game screen up makes Hatari redraw those lines.  This blob runs first at game entry: when the booted mode is
; note: 60 Hz (bit 1 of $ff820a clear) it writes 50 Hz, waits FRAMES frame starts (the video address counter falls back to the base;
; note: no interrupts needed, bounded polls), lets the next frame run ~50 display lines and writes the booted mode back.  At 50 Hz
; note: (TOS 1.x / PAL) it does nothing.  d0-d4/a0 are saved.
; note: Site: the game's first instruction `lea $2d446.l,a7` at $800 (the trampoline ends in `jmp $800.w`); the blob replays it (so the
; note: blip runs on the game's stack) and continues at $806.
FRAMES  equ 4

        org     $800
        jmp     $b9200.l

        org     $b9200
        lea     $2d446.l,a7
        movem.l d0-d4/a0,-(a7)
        move.b  $ffff820a.w,d3          ; the sync mode TOS booted with
        btst    #1,d3
        bne.s   .out                    ; bit 1 set = 50 Hz: nothing to clean
        lea     $ffff8205.w,a0          ; video address counter (high, mid) for movep.w
        move.b  #2,$ffff820a.w          ; 50 Hz
        moveq   #FRAMES-1,d4
.fr:    move.w  #20000,d2               ; bounded poll: ~5 frames of reads
        movep.w 0(a0),d1
.l:     movep.w 0(a0),d0
        cmp.w   d0,d1
        bhi.s   .nxt                    ; counter fell back to the base = new frame
        move.w  d0,d1
        dbra    d2,.l
.nxt:   dbra    d4,.fr
        move.w  #20000,d2               ; now just after a frame start: let it run ~50 display lines, then restore
        movep.w 0(a0),d1
.m:     movep.w 0(a0),d0
        sub.w   d1,d0
        cmp.w   #$20,d0
        bcc.s   .go
        dbra    d2,.m
.go:    move.b  d3,$ffff820a.w          ; back to the booted mode
.out:   movem.l (a7)+,d0-d4/a0
        jmp     $806.l
