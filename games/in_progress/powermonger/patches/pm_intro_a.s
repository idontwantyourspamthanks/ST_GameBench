; name: pm_intro_a
; default: yes
; stage: 1
; site: $1428
; orig: 203c0000000f
; note: PMTT, work/notes/tt.md.  Real-time pacing of the intro (stage 1).  The intro's pictures, text and animations are timed by three
;       CPU busy loops (`move.l #n,d0 / move.l #m,d1 / subi.l #1,d1 / bne.w`), not by the VBL:
;         $1428  15 x $500 iterations: one animation frame step (64 calls),
;         $144a  15 x $800 iterations: the other frame step (145 calls),
;         $146c  $4ff x $500 iterations: the long hold on a picture (3 calls: $6ec, $d3a, $d74).
;       On a 68000 at 8 MHz (ST and STE alike; measured entry to exit in Hatari, `pc = $1428 && ($1428).w = $203c` and the routine's `rts`,
;       original floppy, 50 Hz: $1428 = 4.94 VBL, $144a = 7.92 VBL, $146c = 420.3 VBL, i.e. 98.8 ms, 158.4 ms, 8.41 s) they last as the author
;       intended; a Mega STE at 16 MHz plays the intro twice as fast and a TT (68030, 32 MHz, caches off) about ten times as fast (text and
;       castle pictures flash by, the fades are instant, the credits loop comes at once).
;       The three routines are replaced by waits in real time: a fixed number of 1/300 s units (the unit of tick_head: a VBL is 6 units at 50 Hz,
;       5 at 60 Hz, read from the shifter sync mode $ff820a bit 1 at every VBL): $1428 = 30 (100 ms), $144a = 48 (160 ms), $146c = 2522 (8.41 s).
;       Each wait polls the intro's own VBL flag `$2ca0` (the stage-1 VBL handler `$2c78` sets it to 1 every frame; `clr.w` first so a stale
;       flag is not a frame) and subtracts one VBL's worth of units until nothing is left; the overshoot (0..5 units, at 60 Hz) is carried to the
;       next call (CARRY), so the long-run rate is exact at both refresh rates and the 8 MHz ST/STE durations stay within a VBL of the original.
;       The routines clobber d0/d1 only and return with `rts` (they are `jsr`/`bsr` targets): the entry stubs below do the same.  The skip key
;       (space, checked by the VBL handler itself) works as in the original.
        org     $1428
        jmp     $cd780.l

        org     $cd780
wa:     moveq   #30,d0
        bra.s   wt
wb:     moveq   #48,d0
        bra.s   wt
wc:     move.l  #2522,d0
wt:     move.l  d2,-(a7)
        move.w  CARRY(pc),d2
        ext.l   d2
        add.l   d2,d0                   ; units + (negative) carry
.loop:  clr.w   $2ca0.l                 ; the next VBL sets it
.w:     cmpi.w  #1,$2ca0.l
        bne.s   .w
        moveq   #5,d1                   ; 60 Hz: 5 units per VBL
        btst    #1,$ffff820a.w          ; shifter sync mode: bit 1 set = 50 Hz
        beq.s   .r
        moveq   #6,d1                   ; 50 Hz: 6 units per VBL
.r:     sub.l   d1,d0
        bgt.s   .loop
        move.w  d0,CARRY                ; <= 0: the overshoot, owed to the next wait
        move.l  (a7)+,d2
        rts
CARRY:  dc.w    0
