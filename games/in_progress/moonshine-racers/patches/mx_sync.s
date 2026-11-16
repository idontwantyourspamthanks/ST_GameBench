; name: mx_sync
; default: no
; site: $7b74
; orig: 4eb90000d1e4
; requires: mt_clock mt_pre mx_pre                ; clock/PEND, latch guard, slot copy of the object draw
; conflicts: mt_sync                              ; replaces it (same site $7b74, same blob $B8100, same data $B8F04)
; data: $B8F04 4
; data: $B8F20 224
; data: $B9000 3584
; note: Needs mx_pre (site $7b46) for the slot state the object draw saw: without it no extra frame is drawn.
; doc: EXPERIMENTAL (visible: adds new pictures).  Replaces mt_sync (use with mt_clock + mt_pre, NOT mt_sync): the fixed-tick pacer, and in the idle time of each tick extra frames drawn at a pose extrapolated from the last logic step.
; note: Extra frames between logic ticks (work/notes/extrap.md).  Site $7b74 `jsr $d1e4.l` (end of the race pass) -> `jsr $B8100.l` (same site as mt_sync, so the two exclude each other).
; note: newsync = mt_sync's flip + latch flag + sleep until the tick, plus: publish the raster-band words right after the flip, and `extras` ($B8400) in the idle time.
; note: extras: while time remains before the next tick (deadline rule, CLK in 1/300 s), draw another frame of the SAME logic step with the camera advanced by k = f*speed world
; note: units (f = display time since the main frame / TICK): the rings fe50/ff76/1003c, the road geometry (stripe phase), the scroll, object distances, AI-car distances and the lateral
; note: position are advanced; all game logic is NOT run; every word the advance changed is restored before the tick (group-end state == stock, display scratch excluded).
; note: Kill switch: byte $B8F20 (X_OFF) != 0 -> plain mt_sync behaviour.  Test: byte $B8F21 (X_TEST) = n -> exactly n extras per tick at f = j/(n+1), no timing, no latch guard; n+$80 -> n extras with zero advance (they must reproduce the main frame).
TICK    equ     36
MAXLAG  equ     2*TICK
SAFE    equ     0
MAXV    equ     31
CLK     equ     $B8F00
NEXT    equ     $B8F04
PEND    equ     $B8F08
X_OFF   equ     $B8F20          ; byte: kill switch
X_TEST  equ     $B8F21          ; byte: test mode
LATP    equ     $B8F22          ; word: $1318 at the previous tick
DEXT    equ     $B8F24          ; word: extra-frame duration estimate (clock units)
DPREV   equ     $B8F26          ; word: running average of the measured extra-frame duration (clock units * 16)
KCUM    equ     $B8F28          ; word: world units advanced so far in this group
KNEW    equ     $B8F2A          ; word: target for the frame being drawn
V       equ     $B8F2C          ; word: speed ($130c) of the tick
LAT0    equ     $B8F2E          ; word: $1318 of the tick
DLAT    equ     $B8F30          ; word: lateral change per tick
NEXTRA  equ     $B8F32          ; word: extra frames drawn in this group
TMAIN   equ     $B8F34          ; long: display time of the main frame (CLK units)
NFRAMES equ     $B8F38          ; long: statistics: extra frames drawn since the start
NGROUPS equ     $B8F3C          ; long: statistics: ticks that drew at least one extra frame
NTICKS  equ     $B8F40          ; long: statistics: ticks that entered the group code
FIDX    equ     $B8F44          ; word: next slot of the flip log
TSTART  equ     $B8F48          ; long: clock at the start of the extra frame being drawn
VBLU    equ     $B8F4C          ; word: clock units per VBL (6 at 50 Hz, 5 at 60 Hz)
PREBUF  equ     $B9E00          ; mx_pre: x/y long of the 48 object slots before the main frame's object draw
PREV    equ     $B9E00+$A80     ; mx_pre: PREBUF is valid for this tick
NOWANT  equ     $B8F50          ; byte: no extra frame fitted into the last tick: mx_pre does not copy the slots
TKLEN   equ     28              ; ticker state $1198-$11b3
TSAVE   equ     $B9DC0          ; its saved copy (+ the face word $10f8 at +TKLEN)
RSN     equ     $B8F54          ; 11 words: ticks that skipped the extra frames, by reason (0 no slot copy, 1 off, 2 standing, 3 too fast, 4 $1024, 5 $1021, 6 ticker char, 7 erase, 8 request)
FLOG    equ     $B8F80          ; 32 words: CLK (low word) at each flip, main and extra
KLOG    equ     $B8FC0          ; 32 words: world units advanced (0 = main frame) at that flip
UNDO    equ     $B9000
U_SLOT  equ     UNDO+$0C0       ; saved copy of the object slots $2c68-$36e7 (2688 bytes)
U_WIN   equ     UNDO+$B40       ; saved ring head windows
U_KERN  equ     UNDO+$BE0       ; saved sprite-kernel patch longs (100 x 4 bytes)

        org     $7b74
        jsr     $B8100.l

        org     $B8100
newsync:
        jsr     $d1ca.l                 ; flip (unchanged routine)
        move.b  #1,PEND.l               ; its latch is now pending
        clr.b   $611a.l                 ; keep the stock meaning of $611a for any other user
        move.w  $1302.w,$12fe.w         ; raster-band words of the frame just flipped (the VBL ISR reads them
        move.w  $1304.w,$1300.w         ; at the VBL that latches it); the tail at $7b7a copies the same values again
        moveq   #0,d0
        jsr     $B8380.l                ; flip log
        jsr     $B8400.l                ; extra frames (all game state restored on return)
.rd:    move.l  CLK.l,d0                ; torn-read safe long read
        cmp.l   CLK.l,d0
        bne.s   .rd
        sub.l   NEXT.l,d0               ; lag = now - next
        bmi.s   .rd                     ; not due yet: sleep until the tick
        cmp.l   #MAXLAG,d0
        bls.s   .ok
        move.l  CLK.l,d0                ; more than MAXLAG behind: resync, no burst
        cmp.l   CLK.l,d0
        bne.s   .rd
        move.l  d0,NEXT.l
.ok:    add.l   #TICK,NEXT.l
        rts

        org     $B8380
logf:   move.w  FIDX.l,d1               ; d0 = world units advanced by the frame just flipped
        and.w   #31,d1
        add.w   d1,d1
        lea     FLOG.l,a0
        move.w  CLK+2.l,(a0,d1.w)
        lea     KLOG.l,a0
        move.w  d0,(a0,d1.w)
        lsr.w   #1,d1
        addq.w  #1,d1
        move.w  d1,FIDX.l
        rts

        org     $B8400
extras:
        move.w  $1318.w,d0              ; lateral position, tracked every tick
        move.w  LATP.l,d1
        move.w  d0,LATP.l
        sub.w   d1,d0                   ; lateral change since the previous tick
        cmp.w   #-12,d0
        blt.s   .nl
        cmp.w   #12,d0
        ble.s   .lok
.nl:    moveq   #0,d0
.lok:   move.w  d0,DLAT.l
        clr.w   NEXTRA.l
        moveq   #5,d0
        btst    #1,$ffff820a.w          ; bit 1 set = 50 Hz
        beq.s   .hz
        moveq   #6,d0
.hz:    move.w  d0,VBLU.l
        bsr     readclk
        add.w   VBLU.l,d0               ; the flipped frame is displayed from the next VBL
        move.l  d0,TMAIN.l
        tst.b   PREV.l                  ; mx_pre's slot copy of this tick
        bne.s   .pv
        addq.w  #1,RSN+0.l
        bra     wantnext                ; none (NOWANT): does an extra frame fit now?  (tail call; returns to newsync)
.pv:    clr.b   PREV.l
        tst.b   X_OFF.l
        beq.s   .on
        addq.w  #1,RSN+2.l
        rts
.on:    move.w  $130c.w,d2              ; speed of this tick
        bne.s   .mv
        addq.w  #1,RSN+4.l
        rts                             ; standing: the picture would not change
.mv:    cmp.w   #MAXV,d2
        bls.s   .sl
        addq.w  #1,RSN+6.l
        rts                             ; beyond the undo windows
.sl:    tst.b   $1024.w
        beq.s   .r1
        addq.w  #1,RSN+8.l
        rts                             ; not plain racing (finish / start sequences)
.r1:    cmpi.b  #2,$1021.w
        beq.s   .r2
        addq.w  #1,RSN+10.l
        rts
.r2:
.gx:    movem.l d0-d7/a0-a6,-(a7)
        addq.l  #1,NTICKS.l
        move.w  d2,V.l
        move.w  $1318.w,LAT0.l
        clr.w   KCUM.l
.loop:  tst.b   X_TEST.l
        bne     .testplan
        bsr     readclk
        move.l  d0,TSTART.l             ; start clock of this extra frame (the game's routines clobber every register)
        move.l  d0,d6
        moveq   #0,d1
        move.w  DEXT.l,d1
        bne.s   .have
        move.l  TMAIN.l,d1              ; no estimate yet: the main pass's own duration
        sub.w   VBLU.l,d1
        sub.l   NEXT.l,d1
        add.l   #TICK,d1
        cmp.w   VBLU.l,d1
        bgt.s   .have
        move.w  VBLU.l,d1
.have:  move.l  d6,d2
        add.l   d1,d2
        add.l   #SAFE,d2
        cmp.l   NEXT.l,d2               ; flip would come after the next tick is due
        bls.s   .fits
        tst.w   NEXTRA.l                ; no extra frame fitted this tick: forget a stale slow estimate slowly
        bne     .done
        move.w  DEXT.l,d0
        cmp.w   #12,d0
        bls     .done
        subq.w  #1,DEXT.l
        sub.w   #16,DPREV.l
        bra     .done
.fits:
        move.l  d6,d2
        add.l   d1,d2
        add.w   VBLU.l,d2               ; display time of this frame
        sub.l   TMAIN.l,d2              ; elapsed since the main frame (units)
        bmi     .done
        mulu.w  V.l,d2
        add.l   #TICK/2,d2
        divu.w  #TICK,d2
        and.l   #$ffff,d2
        move.w  V.l,d3
        cmp.w   d3,d2
        bls.s   .kok
        move.w  d3,d2
.kok:   cmp.w   KCUM.l,d2
        bls     .done                   ; no new pose to show
        bra.s   .frame
.testplan:
        moveq   #0,d6
        moveq   #0,d2
        move.b  X_TEST.l,d2
        move.w  NEXTRA.l,d3
        bclr    #7,d2
        sne     d7                      ; X_TEST bit 7: zero-advance frames (the picture must equal the main frame)
        cmp.w   d2,d3
        bhs     .done
        tst.b   d7
        beq.s   .tk
        moveq   #0,d2
        bra     .frame
.tk:    addq.w  #1,d3                   ; j = 1..n
        move.w  V.l,d4
        mulu.w  d3,d4
        addq.w  #1,d2
        move.w  d2,d5
        lsr.w   #1,d5
        add.w   d5,d4                   ; + (n+1)/2
        and.l   #$ffff,d4
        divu.w  d2,d4
        moveq   #0,d2
        move.w  d4,d2                   ; k = round(j*V/(n+1))
        cmp.w   KCUM.l,d2
        bls     .done
.frame: move.w  d2,KNEW.l
        tst.w   NEXTRA.l
        bne.s   .sv0
        bsr     saveundo                ; lazily: only when a first extra frame is really drawn
        clr.b   $11ce.w                 ; the HUD item $f620 plays its alarm sound once for this flag: the main frame does that (flag restored below)
.sv0:   move.w  KNEW.l,d2
        sub.w   KCUM.l,d2               ; world units to advance now
        move.w  d2,$130c.w
        bsr     setlat
        jsr     $fe50.l                 ; the three rings consume $130c samples
        jsr     $ff76.l
        jsr     $1003c.l
        movea.l $1008.w,a5
        jsr     $17c24.l                ; span buffer clear + road geometry (advances the stripe phase)
        jsr     $100b4.l
        tst.b   X_TEST.l
        bne.s   .go
.g:     tst.b   PEND.l                  ; the flipped buffer must be on screen before the first write
        bne.s   .g
.go:    jsr     $17c42.l                ; road
        jsr     $10a5e.l
        jsr     $10a98.l                ; horizon scroll (advances by $130c)
        bsr     prerestore              ; the slots as the main frame's object draw found them
        move.w  KNEW.l,$130c.w          ; (they hold the main frame's pose: advance by the total)
        jsr     $e2e8.l                 ; object distances -= $130c
        bsr     carstep
        move.w  V.l,$130c.w             ; the HUD reads the real speed
        jsr     $e316.l                 ; object projection
        jsr     $dd50.l                 ; clouds
        jsr     $18318.l                ; horizon strip
        jsr     $e406.l                 ; objects
        move.w  UNDO+8.l,$11ca.w        ; bottom-left puff animation ($f134 advances its frame per call): the extra frames show the frame
        bsr     hud                     ; the next main frame will show, not a faster animation
        jsr     $d1ca.l                 ; flip
        move.b  #1,PEND.l
        move.w  $1302.w,$12fe.w
        move.w  $1304.w,$1300.w
        addq.l  #1,NFRAMES.l
        move.w  KNEW.l,d0
        jsr     $B8380.l
        tst.b   X_TEST.l
        bne.s   .mdone
        bsr     readclk
        sub.l   TSTART.l,d0             ; duration in clock units (VBL granular)
        cmp.w   VBLU.l,d0
        bge.s   .dm
        move.w  VBLU.l,d0
.dm:    lsl.w   #4,d0                   ; running average of the measured duration, units * 16 (the clock only ticks per VBL: a frame of
        move.w  DPREV.l,d1              ; 1.1 VBL measures 1 or 2 VBL; the average converges on the real duration)
        beq.s   .dm0
        sub.w   d1,d0
        asr.w   #2,d0
        add.w   d1,d0
.dm0:   move.w  d0,DPREV.l
        add.w   #15,d0
        lsr.w   #4,d0
        move.w  d0,DEXT.l               ; units, rounded up
.mdone: move.w  KNEW.l,KCUM.l
        addq.w  #1,NEXTRA.l
        bra     .loop
.done:  tst.w   NEXTRA.l
        beq.s   .none
        addq.l  #1,NGROUPS.l
        bsr     restoreundo
.none:  bsr     wantnext
        movem.l (a7)+,d0-d7/a0-a6
        rts

; does an extra frame fit into a tick?  NOWANT (mx_pre skips the slot copy) = 0 if it did this tick or would have: the time left now (clock units) holds one more
; frame of the estimated duration (the main frame's own duration while nothing was measured)
wantnext:
        clr.b   NOWANT.l
        tst.w   NEXTRA.l
        bne.s   .r
        tst.b   X_TEST.l                ; test mode: always copy
        bne.s   .r
        bsr     readclk
        move.l  NEXT.l,d1
        sub.l   d0,d1                   ; time left in the tick
        moveq   #0,d2
        move.w  DEXT.l,d2
        bne.s   .e
        move.l  TMAIN.l,d2
        sub.w   VBLU.l,d2
        sub.l   NEXT.l,d2
        add.l   #TICK,d2
.e:     add.l   #SAFE,d2
        cmp.l   d2,d1
        bge.s   .r
        move.b  #1,NOWANT.l
.r:     rts

readclk:
.r:     move.l  CLK.l,d0
        cmp.l   CLK.l,d0
        bne.s   .r
        rts

; lateral position of the frame: LAT0 + round(DLAT * KNEW / V)
setlat: move.w  DLAT.l,d0
        beq.s   .z
        muls.w  KNEW.l,d0
        move.w  V.l,d1
        move.w  d1,d2
        lsr.w   #1,d2
        ext.l   d2
        tst.l   d0
        bpl.s   .p
        sub.l   d2,d0
        bra.s   .d
.p:     add.l   d2,d0
.d:     divs.w  d1,d0
.z:     add.w   LAT0.l,d0
        move.w  d0,$1318.w
        rts

prerestore:
        lea     PREBUF.l,a0
        lea     $2c68.w,a1
        moveq   #55,d7
.l:     movem.l (a0)+,d0-d6/a2-a6
        movem.l d0-d6/a2-a6,(a1)
        lea     48(a1),a1
        dbra    d7,.l
        rts

; AI cars ($2ca0 + n*$38, n = 0..3), slots freshly restored: distance $20 -= round((V - speed $22) * KNEW / V); only inside 0..$3ff and only while visible (bit 0 of $4)
carstep:
        lea     $2ca0.w,a0
        moveq   #3,d7
.c:     btst    #6,4(a0)
        bne.s   .n
        btst    #0,4(a0)
        beq.s   .n
        move.w  V.l,d1
        tst.w   $1030.w
        beq.s   .s
        sub.w   $22(a0),d1
.s:     muls.w  KNEW.l,d1
        move.w  V.l,d2
        divs.w  d2,d1
        move.w  $20(a0),d0
        sub.w   d1,d0
        bmi.s   .n
        cmp.w   #$400,d0
        bge.s   .n
        move.w  d0,$20(a0)
.n:     lea     $38(a0),a0
        dbra    d7,.c
        rts

; the HUD part of the pass ($ef7a) without the message ticker ($11ef0: it counts frames)
hud:    movea.l $1008.w,a5
        jsr     $de1c.l
        jsr     $f1c0.l
        jsr     $efc6.l
        jsr     $f214.l
        movea.l $1008.w,a5
        jsr     $f3b6.l
        jsr     $f430.l
        jsr     $f53c.l
        lea     TSAVE.l,a0              ; the message ticker ($11ef0) counts frames and draws a typed character / the end-of-message erase into the
        lea     $1198.w,a1              ; buffer of its call and again into the other buffer at the next call: run it here with its state saved
        moveq   #(TKLEN/2)-1,d0         ; and restored (the extra frame's buffer gets the next step early, the main frame then does the real one)
.ts:    move.w  (a1)+,(a0)+
        dbra    d0,.ts
        move.w  $10f8.w,TSAVE+TKLEN.l
        jsr     $11ef0.l
        lea     TSAVE.l,a0
        lea     $1198.w,a1
        moveq   #(TKLEN/2)-1,d0
.tr:    move.w  (a0)+,(a1)+
        dbra    d0,.tr
        move.w  TSAVE+TKLEN.l,$10f8.w
        jsr     $f90c.l
        jsr     $f620.l
        jsr     $f76a.l
        jsr     $f7f0.l
        jsr     $de6c.l
        jsr     $f22c.l
        jsr     $f134.l
        rts

; ---- undo of the advance ---------------------------------------------------------------------------------------------------------
; static ranges (word address, length in bytes), terminated by 0
UTAB:   dc.w    $10bc,2                 ; HUD 'last drawn' / 'redraw once more for the other buffer' flags: the pass that follows must
        dc.w    $11c4,12                ; take the draw decisions the unmodified game takes (every flagged part is a complete redraw)
        dc.w    $10ec,14                ; face animation state of the HUD (random lip movement counts frames)
        dc.w    $12f8,6
        dc.w    $1308,4
        dc.w    $1316,16
        dc.w    $13a2,16
        dc.w    $1bb0,12
        dc.w    $23bc,12
        dc.w    $27c8,38
        dc.w    $29c8+0*$38,4
        dc.w    $29c8+1*$38,4
        dc.w    $29c8+2*$38,4
        dc.w    $29c8+3*$38,4
        dc.w    $29c8+4*$38,4
        dc.w    $29c8+5*$38,4
        dc.w    $29c8+6*$38,4
        dc.w    $29c8+7*$38,4
        dc.w    $29c8+8*$38,4
        dc.w    $29c8+9*$38,4
        dc.w    $29c8+10*$38,4
        dc.w    $29c8+11*$38,4
        dc.w    0
; ring windows: base, index address, index mask, window bytes
RTAB:   dc.w    $13b0,$13ae,$3ff,32
        dc.w    $17b0,$13ae,$3ff,32
        dc.w    $1bbc,$1bba,$7ff,64
        dc.w    $23c8,$23c6,$3ff,32
        dc.w    0

; self-modified immediates of the sprite kernels ($12000-$16000): the pass patches them per sprite and a few sprites use a stale one, so the
; main frame depends on what was drawn last; every long the unmodified game patches over a whole race is listed (work/extrap/kern_union.py)
KTAB:   dc.l    $dafe                   ; the HUD face's own random generator (an immediate at $dafe; the game logic RNG is $dae6)
        dc.l    $12a66,$12a74,$12b6a,$12b82,$12c7e,$12c96
        dc.l    $12db8,$12dc8,$12ffa,$13010,$1308e,$1309c
        dc.l    $130b6,$1317c,$13192,$13210,$13228,$13248
        dc.l    $13318,$1332e,$133ac,$133c4,$133e4,$13524
        dc.l    $13538,$135bc,$135da,$135f6,$1370e,$13724
        dc.l    $1373e,$137d0,$137ec,$13804,$13820,$138f8
        dc.l    $1390e,$13928,$139ba,$139e0,$13a02,$13a28
        dc.l    $13b0a,$13b20,$13b3a,$13bcc,$13bf2,$13c14
        dc.l    $13c3a,$13d9c,$13db0,$13dc8,$13e68,$13e98
        dc.l    $13eba,$13ef2,$14030,$14046,$14060,$14076
        dc.l    $1411e,$1413a,$14152,$14184,$141a0,$1428e
        dc.l    $142a4,$142be,$142d4,$1437c,$143a2,$143c4
        dc.l    $14400,$14426,$1451e,$14534,$1454e,$14564
        dc.l    $1460a,$14630,$14652,$1468e,$146b4,$1483e
        dc.l    $14852,$1486a,$14888,$1493e,$1496e,$14998
        dc.l    $149e4,$14a14,$15858,$15868,$15ad6,$15ae6
        dc.l    $15d54,$15d64,$15f1e,$15f22
        dc.l    0

saveundo:
        lea     UNDO.l,a1
        lea     UTAB(pc),a2
.l:     move.w  (a2)+,d0
        beq.s   .rings
        movea.w d0,a0
        move.w  (a2)+,d1
        lsr.w   #1,d1
        subq.w  #1,d1
.c:     move.w  (a0)+,(a1)+
        dbra    d1,.c
        bra.s   .l
.rings: lea     U_WIN.l,a1
        lea     RTAB(pc),a2
.rl:    move.w  (a2)+,d0
        beq.s   .slots
        movea.w d0,a0                   ; ring base
        movea.w (a2)+,a3                ; index address
        move.w  (a3),d2                 ; index
        move.w  (a2)+,d3                ; mask
        move.w  (a2)+,d1                ; window length
        subq.w  #1,d1
.rc:    and.w   d3,d2
        move.b  (a0,d2.w),(a1)+
        addq.w  #1,d2
        dbra    d1,.rc
        bra.s   .rl
.slots: lea     $2c68.w,a0
        lea     U_SLOT.l,a1
        move.w  #($36e8-$2c68)/4-1,d1
.sc:    move.l  (a0)+,(a1)+
        dbra    d1,.sc
        lea     U_KERN.l,a1
        lea     KTAB(pc),a2
.kl:    move.l  (a2)+,d0
        beq.s   .kd
        movea.l d0,a0
        move.l  (a0),(a1)+
        bra.s   .kl
.kd:    rts

restoreundo:
        lea     UNDO.l,a0
        lea     UTAB(pc),a2
.l:     move.w  (a2)+,d0
        beq.s   .rings
        movea.w d0,a1
        move.w  (a2)+,d1
        lsr.w   #1,d1
        subq.w  #1,d1
.c:     move.w  (a0)+,(a1)+
        dbra    d1,.c
        bra.s   .l
.rings: lea     U_WIN.l,a0
        lea     RTAB(pc),a2
.rl:    move.w  (a2)+,d0
        beq.s   .slots
        movea.w d0,a1                   ; ring base
        movea.w (a2)+,a3
        move.w  (a3),d2                 ; index (already restored by the static ranges)
        move.w  (a2)+,d3
        move.w  (a2)+,d1
        subq.w  #1,d1
.rc:    and.w   d3,d2
        move.b  (a0)+,(a1,d2.w)
        addq.w  #1,d2
        dbra    d1,.rc
        bra.s   .rl
.slots: lea     U_SLOT.l,a0
        lea     $2c68.w,a1
        move.w  #($36e8-$2c68)/4-1,d1
.sc:    move.l  (a0)+,(a1)+
        dbra    d1,.sc
        lea     U_KERN.l,a0
        lea     KTAB(pc),a2
.kl:    move.l  (a2)+,d0
        beq.s   .kd
        movea.l d0,a1
        move.l  (a0)+,(a1)
        bra.s   .kl
.kd:    move.w  V.l,$130c.w
        rts
