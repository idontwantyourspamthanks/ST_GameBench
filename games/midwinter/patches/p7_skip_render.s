; name: p7_skip_render
; default: yes
; site: $14e50
; orig: 4eb90001d0a0
; data: $b6000 2112
; note: P7 static-frame skip (work/notes/p7_static_skip.md), part 2/2 (needs p7_skip_sky; without it the hook never skips).
; note: Hook on the marker call `jsr $1d0a0` of the frame sub_014e00 ($14e50), the first of the five render calls that follow the
; note: object logic: markers $1d0a0, geometry $18304, raster $19ce2, goggles replay $1bbe6 (the sky fill $1580e is deferred to this
; note: hook by p7_skip_sky).  When nothing the 3D window depends on has changed since the picture that now sits in the draw
; note: buffer was rendered, the hook drops `$1d0a0 $18304 $19ce2 $1bbe6` (and the deferred sky fill) and continues at $14e72
; note: (after the replay) with the two stores the skipped calls make that others read: $1bbe2 := draw buffer ($14e62) and
; note: $14134 := 0 (first instruction of the raster, the pick result is only ever set when $12d3a = 4).  HUD, logic, message,
; note: flip are untouched.  Inputs = the bytes the render reads that something outside it writes (traced, see the note):
; note: view position/cell/offsets $12c60-$12c83, heading $12c98, $157a8, $159a0, view vectors/tilt/height $171f0-$1721d, window
; note: origin $19cd4, marker count $1d418, light vector $1d816, $1cd64/66, sky selector $12d54, goggles list pointer $1bbde,
; note: the four object slots ($1cd7e + n*$2c: flag, and when active inside +-4700 units of the player the fields the object draw
; note: reads) and the marker records $70010 (copied/compared whole).  A generation counter GEN is raised whenever the staged
; note: signature or the marker table differs from the last seen one; GENB[b] = GEN of the last render into buffer b (b = bit 16 of
; note: $12d0a - 5), so a skip needs the last three presented frames to come from identical inputs (triple buffer $58000/$68000/$78000).
; note: No skip (render, GENB[b] := 0): caller of the frame is not the loop ($14ac4: first frame, re-entry: all GENB cleared), mode
; note: step is not $131ae, message timer $14ee4 >= 0, $12d3a = 4 (pick mode), $13b40 = 0 (first frame, no flip), a slot with $26 = 0
; note: inside the window (the $20e4e effect path), more than 96 marker records, unknown buffer address, PEND = 0.
; note: Data block D = $b6000: ENABLE.w +0 PEND.w +2 GEN.w +4 GENB.w[3] +6 RET.l +12 NSKIP.l +16 NREND +20 NCHG +24 NMK +28 NFORCE +32
; note: NINV +36 NUNS +40; LAST (signature, 248 B) +$40, STG +$140, MKLAST (marker copy, 96 records) +$240.
D       equ     $b6000
oENABLE equ     0
oPEND   equ     2
oGEN    equ     4
oGENB   equ     6
oRET    equ     12
oNSKIP  equ     16
oNREND  equ     20
oNCHG   equ     24
oNMK    equ     28
oNFORCE equ     32
oNINV   equ     36
oNUNS   equ     40
oLAST   equ     $40
oSTG    equ     $140
oMK     equ     $240
SCL     equ     248
MKMAX   equ     96
WIN     equ     4700

        org     $14e50
        jsr     $b5840.l

        org     $b5840
HB:     movem.l d0-d7/a0-a6,-(a7)       ; 60 bytes: hook return at 60(a7), the frame's return at 64(a7)
        lea     D.l,a6
        move.w  #1,oENABLE(a6)
        move.l  $12d0a.l,d7
        swap    d7
        subq.w  #5,d7                   ; buffer index b: $58000 / $68000 / $78000 -> 0 / 1 / 2
        cmp.w   #2,d7
        bhi     .render                 ; unknown buffer: as before, no state
        cmpi.l  #$14ac4,64(a7)
        bne     .reent                  ; not the loop ($14a86 first frame, $d1de): everything is redrawn
        tst.w   oPEND(a6)
        beq     .force                  ; the sky fill already ran in place (p7_skip_sky absent / first pass)
        cmpi.l  #$131ae,$12d5e.l
        bne     .force                  ; snipe, buggy, glider: other overlays and inputs, not traced
        tst.w   $14ee4.l
        bpl     .force                  ; "ENEMY IN RANGE" is drawn into the window after the replay
        cmpi.w  #4,$12d3a.l
        beq     .force                  ; pick mode: the raster sets $14134
        tst.w   $13b40.l
        beq     .force                  ; first frame after a reset: no flip this pass
        lea     oSTG(a6),a2
        lea     $12c60.l,a0
        movem.l (a0),d0-d6/a3-a4        ; $12c60-$12c83: position, cells, offsets, view origin (9 longs)
        movem.l d0-d6/a3-a4,(a2)
        lea     36(a2),a2
        move.w  $12c98.l,(a2)+          ; heading
        move.w  $157a8.l,(a2)+
        move.l  $159a0.l,(a2)+          ; roll
        lea     $171f0.l,a0
        movem.l (a0),d0-d6/a1/a3-a5     ; $171f0-$1721b: window, view vectors, tilt (11 longs)
        movem.l d0-d6/a1/a3-a5,(a2)
        lea     44(a2),a2
        move.w  $1721c.l,(a2)+          ; camera height
        move.l  $19cd4.l,(a2)+          ; window origin on the map
        move.w  $1d418.l,(a2)+          ; marker count - 1
        move.w  $1d816.l,(a2)+          ; light vector
        move.l  $1d818.l,(a2)+
        move.l  $1cd64.l,(a2)+
        move.w  $12d54.l,(a2)+          ; sky pattern selector
        move.l  $1bbde.l,(a2)+          ; goggles list pointer
        moveq   #0,d3                   ; d3 <> 0: unsupported content
        moveq   #0,d4                   ; d4 <> 0: inputs changed
        lea     $1cd7e.l,a0             ; the four object slots
        moveq   #3,d6
.slot:  tst.w   $26(a0)
        bmi.s   .sinact
        move.l  6(a0),d0
        sub.l   $12c60.l,d0
        bpl.s   .sx
        neg.l   d0
.sx:    cmp.l   #WIN,d0
        bgt.s   .sout
        move.l  $a(a0),d0
        sub.l   $12c64.l,d0
        bpl.s   .sy
        neg.l   d0
.sy:    cmp.l   #WIN,d0
        bgt.s   .sout
        tst.w   $26(a0)
        bne.s   .sok
        moveq   #1,d3                   ; state 0 inside the window: the $20e4e effect path, not modelled
.sok:   move.w  #$7fff,(a2)+
        move.w  (a0),(a2)+
        move.l  2(a0),(a2)+
        move.l  6(a0),(a2)+
        move.l  $a(a0),(a2)+
        move.w  $e(a0),(a2)+
        move.w  $10(a0),(a2)+
        move.w  $12(a0),(a2)+
        move.w  $14(a0),(a2)+
        move.w  $16(a0),(a2)+
        move.w  $18(a0),(a2)+
        move.w  $1a(a0),(a2)+
        move.w  $24(a0),(a2)+
        move.w  $26(a0),(a2)+
        bra.s   .snext
.sout:  move.w  #$7ffe,(a2)+
        bra.s   .spad
.sinact:
        move.w  #$8000,(a2)+
.spad:  moveq   #0,d0
        move.l  d0,(a2)+
        move.l  d0,(a2)+
        move.l  d0,(a2)+
        move.l  d0,(a2)+
        move.l  d0,(a2)+
        move.l  d0,(a2)+
        move.l  d0,(a2)+
        move.l  d0,(a2)+
.snext: lea     $2c(a0),a0
        dbra    d6,.slot
        lea     oSTG(a6),a0             ; compare with the last signature
        lea     oLAST(a6),a1
        moveq   #SCL/4-1,d0
.cmp:   cmpm.l  (a0)+,(a1)+
        dbne    d0,.cmp
        beq.s   .same
        lea     oSTG(a6),a0
        lea     oLAST(a6),a1
        moveq   #SCL/4-1,d0
.cpy:   move.l  (a0)+,(a1)+
        dbra    d0,.cpy
        moveq   #1,d4
.same:  move.w  $1d418.l,d0             ; marker records (count - 1 in $1d418, negative = none)
        bmi     .nomk
        cmp.w   #MKMAX-1,d0
        bhi     .mkbig
        lea     $70010.l,a0
        lea     oMK(a6),a1
        tst.w   d4
        bne.s   .mkcopy                 ; the signature changed anyway: refresh the copy
.mkcmp: cmpm.l  (a0)+,(a1)+
        bne.s   .mkdiff
        cmpm.l  (a0)+,(a1)+
        bne.s   .mkdiff
        cmpm.l  (a0)+,(a1)+
        bne.s   .mkdiff
        cmpm.l  (a0)+,(a1)+
        bne.s   .mkdiff
        dbra    d0,.mkcmp
        bra.s   .nomk
.mkdiff:
        addq.l  #1,oNMK(a6)
        moveq   #1,d4
        move.w  $1d418.l,d0
        lea     $70010.l,a0
        lea     oMK(a6),a1
.mkcopy:
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        dbra    d0,.mkcopy
        bra.s   .nomk
.mkbig: moveq   #1,d3                   ; more records than the copy holds
.nomk:  tst.w   d4
        beq.s   .nochg
        addq.l  #1,oNCHG(a6)
        addq.w  #1,oGEN(a6)
        bne.s   .nochg
        move.w  #1,oGEN(a6)             ; 0 is "no render yet"
.nochg: move.w  d7,d5
        add.w   d5,d5                   ; d5 = 2b
        tst.w   d3
        bne.s   .unsup
        move.w  oGEN(a6),d0
        beq.s   .rend
        cmp.w   oGENB(a6,d5.w),d0
        beq.s   .skip
        move.w  d0,oGENB(a6,d5.w)       ; this buffer is about to hold a picture of the current inputs
.rend:  addq.l  #1,oNREND(a6)
        bra.s   .render
.unsup: clr.w   oGENB(a6,d5.w)
        addq.l  #1,oNUNS(a6)
        bra.s   .render
.force: move.w  d7,d5
        add.w   d5,d5
        clr.w   oGENB(a6,d5.w)
        addq.l  #1,oNFORCE(a6)
        bra.s   .render
.reent: clr.l   oGENB(a6)               ; first frame / re-entry: the screens are redrawn, forget all pictures
        clr.w   oGENB+4(a6)
        addq.l  #1,oNINV(a6)
.render:
        movem.l (a7)+,d0-d7/a0-a6
        move.l  (a7)+,D+oRET.l          ; the frame's own $14e56 return
        tst.w   D+oPEND.l
        beq.s   .nosky
        clr.w   D+oPEND.l
        jsr     $1580e.l                ; the deferred sky fill, called with the frame's stack layout (p4_pfx_fill: 64(a7))
.nosky: move.l  D+oRET.l,-(a7)
        jmp     $1d0a0.l
.skip:  addq.l  #1,oNSKIP(a6)
        movem.l (a7)+,d0-d7/a0-a6
        addq.l  #4,a7                   ; no return to $14e56: continue after the replay
        clr.w   D+oPEND.l
        move.l  $12d0a.l,$1bbe2.l       ; as $14e62
        clr.w   $14134.l                ; as the raster entry $19d0e
        jmp     $14e72.l
