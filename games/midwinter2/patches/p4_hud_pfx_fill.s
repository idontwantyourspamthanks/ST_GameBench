; name: p4_hud_pfx_fill
; default: yes
; site: $1b996
; orig: 48e7fffe2c78
; phase: deferred
; note: HUD "clean-prefix" set, part 3/4 (work/notes/cockpit.md section 3C).  Sky fill $1b996 (lines
;       58-199, 71 passes of 2 lines).  KB[b] (b = bit 16 of the back buffer base: $60000 -> 0,
;       $70000 -> 1) = number of 8-line blocks from line 58 that already hold the final sky+cockpit
;       image in that buffer (kept by p4_hud_pfx_replay).  Those blocks are not refilled: start line
;       = 58 + 8*KB (a6 += 1280*KB, passes = $46 - 4*KB).  Also resets YMIN (this frame's smallest
;       polygon row) to 200.
;       The fill is also reached from the alternate scene render $327e6 (via $328e2 jsr $505c), which
;       never replays the cockpit: found from the return addresses on entry ((a7) = $1dcaa and 4(a7) =
;       $1dbe2 for $1dbbe -> $505c -> $1dc12, or (a7) = $1dbee for the direct call at $1dbe8).  For any
;       other caller KB[b] is cleared first (full fill, buffer no longer known clean).
KB      equ     $b4680
YMIN    equ     $b4684

        org     $1b996
        jmp     $b4500.l

        org     $b4500
        cmpi.l  #$1dbe2,4(a7)           ; called from the main renderer (path A)?
        beq.s   .main
        cmpi.l  #$1dbee,(a7)            ; direct call at $1dbe8 (path B)?
        beq.s   .main
        move.w  $67a6.w,d0              ; other caller: forget this buffer's clean prefix
        andi.w  #1,d0
        add.w   d0,d0
        lea     KB.l,a0
        clr.w   (a0,d0.w)
.main:  movem.l d0-d7/a0-a6,-(a7)       ; displaced
        movea.l $67a6.w,a6              ; displaced
        move.w  #200,YMIN.l
        move.l  a6,d0
        swap    d0
        andi.w  #1,d0
        add.w   d0,d0
        lea     KB.l,a0
        move.w  (a0,d0.w),d1            ; KB[b]
        move.w  d1,d2
        mulu.w  #1280,d2
        lea     $2440(a6),a6            ; line 58 (orig: move.l #$2440,d0 / adda.l d0,a6)
        adda.l  d2,a6
        lsl.w   #2,d1
        moveq   #$46,d7
        sub.w   d1,d7
        jmp     $1b9a8.l                ; moveq #-1,d0 ...
