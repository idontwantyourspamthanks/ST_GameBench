; name: mf_sync
; default: no
; site: $7b74
; orig: 4eb90000d1e4
; requires: mt_clock mt_pre mf_pre hd_stage       ; clock/PEND, latch guard, slot copy of the object draw (mf_pre); the extra frames draw the new HUD strip (hd_stage's TOPBAR $BB000)
; conflicts: mt_sync mx_sync mx_pre               ; replaces mx_sync (same site $7b74, same blobs/data); mf_pre replaces mx_pre
; data: $B8F04 4
; data: $B8F20 224
; data: $B9000 3584
; doc: Faster extra-frame machinery (replacement of mx_sync, same behaviour and pictures): word/long/movem copies, ring windows sized by the speed, unrolled kernel-table undo.
; note: mf_sync = mx_sync with the undo machinery rewritten (work/notes/mxfast.md): same scheduler (TICK, deadline rule, DEXT), same extra frame (rings, road, horizon, slots, cars, HUD list), same group-end state.
; note: Differences are code only: the static undo ranges are movem.l/move.l (no word loop), the ring windows are saved/restored as aligned longs and only V (rings) / 2V (curve ring) bytes long (an extra advances the rings by at most V samples),
; note: the 48 slots ($2c68-$36e7, 2688 B) are copied as unrolled movem.l bursts (12 registers, -(a1) stores), the 100 kernel longs are copied with `move.l d16(a0),(a1)+` from a base register instead of a table walk.
; note: Needs mf_pre (site $7b46) for the slot state the object draw saw.  Kill switch byte $B8F20 (X_OFF), test byte $B8F21 (X_TEST) as in mx_sync.
TICK    equ     30
MAXLAG  equ     2*TICK
SAFE    equ     0                       ; deadline margin in clock units (negative = an extra may end that much after the tick is due); SAFEX adds a run-time value
SAFEX   equ     $B8F6C                  ; word: run-time margin added to SAFE (signed, clock units; test/tuning, 0 = as mx_sync)
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
TKLEN   equ     28              ; ticker state $1198-$11b3 (the hud: copies below are 7 longs: they assume 28)
TSAVE   equ     $B9DC0          ; its saved copy (+ the face word $10f8 at +TKLEN)
RSN     equ     $B8F54          ; 11 words: ticks that skipped the extra frames, by reason (0 no slot copy, 1 off, 2 standing, 3 too fast, 4 $1024, 5 $1021, 6 ticker char, 7 erase, 8 request)
FLOG    equ     $B8F80          ; 32 words: CLK (low word) at each flip, main and extra
KLOG    equ     $B8FC0          ; 32 words: world units advanced (0 = main frame) at that flip
UNDO    equ     $B9000
U_SLOT  equ     UNDO+$0C0       ; saved copy of the object slots $2c68-$36e7 (2688 bytes; written downwards from U_SLOT+2688, read upwards)
U_WIN   equ     UNDO+$B40       ; saved ring head windows (4 x up to 72 bytes)
U_KERN  equ     UNDO+$BF0       ; saved sprite-kernel patch longs ($dafe + 100 x 4 bytes)

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
        move.w  SAFEX.l,d3              ; (mf) tunable margin
        ext.l   d3
        add.l   d3,d2
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
        jsr     $18318.l                ; horizon strip
        jsr     $e406.l                 ; objects
        bsr     hud
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
        move.w  SAFEX.l,d3
        ext.l   d3
        add.l   d3,d2
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

prerestore:                                     ; slots <- PREBUF (mf_pre wrote it downwards from PREBUF+2688, so it is read upwards and stored downwards)
        lea     PREBUF.l,a0
        lea     $36e8.w,a1
        moveq   #13,d7
.l:     rept    4
        movem.l (a0)+,d0-d6/a2-a6
        movem.l d0-d6/a2-a6,-(a1)
        endr
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

; the HUD part of the pass ($ef7a) without the message ticker's real step: hd_stage's TOPBAR ($BB000: per-buffer shadows, so it needs no undo), the ticker $11ef0 with its state
; saved and restored, the face.  The hit/sound part ($f620's $11ce/$11cf, hd_stage HIT) runs in the main frame only.
hud:    movea.l $1008.w,a5
        jsr     $BB000.l
        movem.l $1198.w,d0-d6           ; the message ticker ($11ef0) counts frames and draws a typed character / the end-of-message erase into the
        movem.l d0-d6,TSAVE.l           ; buffer of its call and again into the other buffer at the next call: run it here with its state saved
        move.w  $10f8.w,TSAVE+TKLEN.l   ; and restored (the extra frame's buffer gets the next step early, the main frame then does the real one)
        jsr     $11ef0.l                ; (mf: the 28-byte state copies are 7 longs by movem, TKLEN = 28)
        movem.l TSAVE.l,d0-d6
        movem.l d0-d6,$1198.w
        move.w  TSAVE+TKLEN.l,$10f8.w
        jsr     $f90c.l
        rts

; ---- undo of the advance ---------------------------------------------------------------------------------------------------------
; Same set as mx_sync (static ranges, ring head windows, 48 slots, kernel longs, $dafe), saved at the first extra of a tick and restored at its end.
; static ranges, packed at UNDO+0 (118 bytes):  $10ec 14, $12f8 6, $1308 4, $1316 16, $13a2 16, $1bb0 12, $23bc 12, $27c8 38
saveundo:
        lea     UNDO.l,a1
        movem.l $10ec.w,d0-d2
        move.w  $10f8.w,d3
        movem.l d0-d2,(a1)
        move.w  d3,12(a1)
        move.l  $12f8.w,d0
        move.w  $12fc.w,d1
        move.l  $1308.w,d2
        move.l  d0,14(a1)
        move.w  d1,18(a1)
        move.l  d2,20(a1)
        movem.l $1316.w,d0-d3
        movem.l $13a2.w,d4-d7
        movem.l d0-d7,24(a1)
        movem.l $1bb0.w,d0-d2
        movem.l $23bc.w,d3-d5
        movem.l d0-d5,56(a1)
        movem.l $27c8.w,d0-d7/a2
        movea.w $27ec.w,a3
        movem.l d0-d7/a2,80(a1)
        move.w  a3,116(a1)
        lea     U_WIN.l,a1
        move.w  V.l,d4
        addq.w  #3,d4                   ; d4 = V + 3
        move.w  d4,d5
        subq.w  #3,d5
        add.w   d5,d5
        addq.w  #3,d5                   ; d5 = 2V + 3
        lea     $13b0.w,a0              ; rings: base, index, mask, window = V / V / 2V / V bytes, copied as aligned longs
        move.w  $13ae.w,d2
        move.w  #$3ff,d3
        move.w  d4,d6
        bsr     .rs
        lea     $17b0.w,a0
        move.w  $13ae.w,d2
        move.w  d4,d6
        bsr     .rs
        lea     $1bbc.w,a0
        move.w  $1bba.w,d2
        move.w  #$7ff,d3
        move.w  d5,d6
        bsr     .rs
        lea     $23c8.w,a0
        move.w  $23c6.w,d2
        move.w  #$3ff,d3
        move.w  d4,d6
        bsr     .rs
        lea     $2c68.w,a0
        lea     U_SLOT+2688.l,a1
        moveq   #13,d7
.sl:    rept    4
        movem.l (a0)+,d0-d6/a2-a6
        movem.l d0-d6/a2-a6,-(a1)
        endr
        dbra    d7,.sl
        lea     U_KERN.l,a1
        move.l  $dafe.l,(a1)+
        lea     $12000.l,a0
        move.l  $a66(a0),(a1)+
        move.l  $a74(a0),(a1)+
        move.l  $b6a(a0),(a1)+
        move.l  $b82(a0),(a1)+
        move.l  $c7e(a0),(a1)+
        move.l  $c96(a0),(a1)+
        move.l  $db8(a0),(a1)+
        move.l  $dc8(a0),(a1)+
        move.l  $ffa(a0),(a1)+
        move.l  $1010(a0),(a1)+
        move.l  $108e(a0),(a1)+
        move.l  $109c(a0),(a1)+
        move.l  $10b6(a0),(a1)+
        move.l  $117c(a0),(a1)+
        move.l  $1192(a0),(a1)+
        move.l  $1210(a0),(a1)+
        move.l  $1228(a0),(a1)+
        move.l  $1248(a0),(a1)+
        move.l  $1318(a0),(a1)+
        move.l  $132e(a0),(a1)+
        move.l  $13ac(a0),(a1)+
        move.l  $13c4(a0),(a1)+
        move.l  $13e4(a0),(a1)+
        move.l  $1524(a0),(a1)+
        move.l  $1538(a0),(a1)+
        move.l  $15bc(a0),(a1)+
        move.l  $15da(a0),(a1)+
        move.l  $15f6(a0),(a1)+
        move.l  $170e(a0),(a1)+
        move.l  $1724(a0),(a1)+
        move.l  $173e(a0),(a1)+
        move.l  $17d0(a0),(a1)+
        move.l  $17ec(a0),(a1)+
        move.l  $1804(a0),(a1)+
        move.l  $1820(a0),(a1)+
        move.l  $18f8(a0),(a1)+
        move.l  $190e(a0),(a1)+
        move.l  $1928(a0),(a1)+
        move.l  $19ba(a0),(a1)+
        move.l  $19e0(a0),(a1)+
        move.l  $1a02(a0),(a1)+
        move.l  $1a28(a0),(a1)+
        move.l  $1b0a(a0),(a1)+
        move.l  $1b20(a0),(a1)+
        move.l  $1b3a(a0),(a1)+
        move.l  $1bcc(a0),(a1)+
        move.l  $1bf2(a0),(a1)+
        move.l  $1c14(a0),(a1)+
        move.l  $1c3a(a0),(a1)+
        move.l  $1d9c(a0),(a1)+
        move.l  $1db0(a0),(a1)+
        move.l  $1dc8(a0),(a1)+
        move.l  $1e68(a0),(a1)+
        move.l  $1e98(a0),(a1)+
        move.l  $1eba(a0),(a1)+
        move.l  $1ef2(a0),(a1)+
        move.l  $2030(a0),(a1)+
        move.l  $2046(a0),(a1)+
        move.l  $2060(a0),(a1)+
        move.l  $2076(a0),(a1)+
        move.l  $211e(a0),(a1)+
        move.l  $213a(a0),(a1)+
        move.l  $2152(a0),(a1)+
        move.l  $2184(a0),(a1)+
        move.l  $21a0(a0),(a1)+
        move.l  $228e(a0),(a1)+
        move.l  $22a4(a0),(a1)+
        move.l  $22be(a0),(a1)+
        move.l  $22d4(a0),(a1)+
        move.l  $237c(a0),(a1)+
        move.l  $23a2(a0),(a1)+
        move.l  $23c4(a0),(a1)+
        move.l  $2400(a0),(a1)+
        move.l  $2426(a0),(a1)+
        move.l  $251e(a0),(a1)+
        move.l  $2534(a0),(a1)+
        move.l  $254e(a0),(a1)+
        move.l  $2564(a0),(a1)+
        move.l  $260a(a0),(a1)+
        move.l  $2630(a0),(a1)+
        move.l  $2652(a0),(a1)+
        move.l  $268e(a0),(a1)+
        move.l  $26b4(a0),(a1)+
        move.l  $283e(a0),(a1)+
        move.l  $2852(a0),(a1)+
        move.l  $286a(a0),(a1)+
        move.l  $2888(a0),(a1)+
        move.l  $293e(a0),(a1)+
        move.l  $296e(a0),(a1)+
        move.l  $2998(a0),(a1)+
        move.l  $29e4(a0),(a1)+
        move.l  $2a14(a0),(a1)+
        move.l  $3858(a0),(a1)+
        move.l  $3868(a0),(a1)+
        move.l  $3ad6(a0),(a1)+
        move.l  $3ae6(a0),(a1)+
        move.l  $3d54(a0),(a1)+
        move.l  $3d64(a0),(a1)+
        move.l  $3f1e(a0),(a1)+
        move.l  $3f22(a0),(a1)+
        rts
.rs:    move.w  d2,d1                   ; a0 ring base, d2 head, d3 mask, d6 = window length + 3, a1 -> window buffer
        and.w   #3,d1
        add.w   d6,d1
        lsr.w   #2,d1
        subq.w  #1,d1                   ; longs - 1
        and.w   #$fffc,d2
.rc:    move.l  (a0,d2.w),(a1)+
        addq.w  #4,d2
        and.w   d3,d2
        dbra    d1,.rc
        rts

restoreundo:
        lea     UNDO.l,a0
        lea     $10ec.w,a1
        movem.l (a0),d0-d2
        move.w  12(a0),d3
        movem.l d0-d2,(a1)
        move.w  d3,$10f8.w
        move.l  14(a0),d0
        move.w  18(a0),d1
        move.l  20(a0),d2
        move.l  d0,$12f8.w
        move.w  d1,$12fc.w
        move.l  d2,$1308.w
        movem.l 24(a0),d0-d7
        movem.l d0-d3,$1316.w
        movem.l d4-d7,$13a2.w
        movem.l 56(a0),d0-d5
        movem.l d0-d2,$1bb0.w
        movem.l d3-d5,$23bc.w
        movem.l 80(a0),d0-d7/a2
        movea.w 116(a0),a3
        movem.l d0-d7/a2,$27c8.w
        move.w  a3,$27ec.w
        lea     U_WIN.l,a0
        move.w  V.l,d4
        addq.w  #3,d4
        move.w  d4,d5
        subq.w  #3,d5
        add.w   d5,d5
        addq.w  #3,d5
        lea     $13b0.w,a1              ; the heads are restored already (static ranges above)
        move.w  $13ae.w,d2
        move.w  #$3ff,d3
        move.w  d4,d6
        bsr     .rs
        lea     $17b0.w,a1
        move.w  $13ae.w,d2
        move.w  d4,d6
        bsr     .rs
        lea     $1bbc.w,a1
        move.w  $1bba.w,d2
        move.w  #$7ff,d3
        move.w  d5,d6
        bsr     .rs
        lea     $23c8.w,a1
        move.w  $23c6.w,d2
        move.w  #$3ff,d3
        move.w  d4,d6
        bsr     .rs
        lea     U_SLOT.l,a0
        lea     $36e8.w,a1
        moveq   #13,d7
.sl:    rept    4
        movem.l (a0)+,d0-d6/a2-a6
        movem.l d0-d6/a2-a6,-(a1)
        endr
        dbra    d7,.sl
        lea     U_KERN.l,a0
        move.l  (a0)+,$dafe.l
        lea     $12000.l,a1
        move.l  (a0)+,$a66(a1)
        move.l  (a0)+,$a74(a1)
        move.l  (a0)+,$b6a(a1)
        move.l  (a0)+,$b82(a1)
        move.l  (a0)+,$c7e(a1)
        move.l  (a0)+,$c96(a1)
        move.l  (a0)+,$db8(a1)
        move.l  (a0)+,$dc8(a1)
        move.l  (a0)+,$ffa(a1)
        move.l  (a0)+,$1010(a1)
        move.l  (a0)+,$108e(a1)
        move.l  (a0)+,$109c(a1)
        move.l  (a0)+,$10b6(a1)
        move.l  (a0)+,$117c(a1)
        move.l  (a0)+,$1192(a1)
        move.l  (a0)+,$1210(a1)
        move.l  (a0)+,$1228(a1)
        move.l  (a0)+,$1248(a1)
        move.l  (a0)+,$1318(a1)
        move.l  (a0)+,$132e(a1)
        move.l  (a0)+,$13ac(a1)
        move.l  (a0)+,$13c4(a1)
        move.l  (a0)+,$13e4(a1)
        move.l  (a0)+,$1524(a1)
        move.l  (a0)+,$1538(a1)
        move.l  (a0)+,$15bc(a1)
        move.l  (a0)+,$15da(a1)
        move.l  (a0)+,$15f6(a1)
        move.l  (a0)+,$170e(a1)
        move.l  (a0)+,$1724(a1)
        move.l  (a0)+,$173e(a1)
        move.l  (a0)+,$17d0(a1)
        move.l  (a0)+,$17ec(a1)
        move.l  (a0)+,$1804(a1)
        move.l  (a0)+,$1820(a1)
        move.l  (a0)+,$18f8(a1)
        move.l  (a0)+,$190e(a1)
        move.l  (a0)+,$1928(a1)
        move.l  (a0)+,$19ba(a1)
        move.l  (a0)+,$19e0(a1)
        move.l  (a0)+,$1a02(a1)
        move.l  (a0)+,$1a28(a1)
        move.l  (a0)+,$1b0a(a1)
        move.l  (a0)+,$1b20(a1)
        move.l  (a0)+,$1b3a(a1)
        move.l  (a0)+,$1bcc(a1)
        move.l  (a0)+,$1bf2(a1)
        move.l  (a0)+,$1c14(a1)
        move.l  (a0)+,$1c3a(a1)
        move.l  (a0)+,$1d9c(a1)
        move.l  (a0)+,$1db0(a1)
        move.l  (a0)+,$1dc8(a1)
        move.l  (a0)+,$1e68(a1)
        move.l  (a0)+,$1e98(a1)
        move.l  (a0)+,$1eba(a1)
        move.l  (a0)+,$1ef2(a1)
        move.l  (a0)+,$2030(a1)
        move.l  (a0)+,$2046(a1)
        move.l  (a0)+,$2060(a1)
        move.l  (a0)+,$2076(a1)
        move.l  (a0)+,$211e(a1)
        move.l  (a0)+,$213a(a1)
        move.l  (a0)+,$2152(a1)
        move.l  (a0)+,$2184(a1)
        move.l  (a0)+,$21a0(a1)
        move.l  (a0)+,$228e(a1)
        move.l  (a0)+,$22a4(a1)
        move.l  (a0)+,$22be(a1)
        move.l  (a0)+,$22d4(a1)
        move.l  (a0)+,$237c(a1)
        move.l  (a0)+,$23a2(a1)
        move.l  (a0)+,$23c4(a1)
        move.l  (a0)+,$2400(a1)
        move.l  (a0)+,$2426(a1)
        move.l  (a0)+,$251e(a1)
        move.l  (a0)+,$2534(a1)
        move.l  (a0)+,$254e(a1)
        move.l  (a0)+,$2564(a1)
        move.l  (a0)+,$260a(a1)
        move.l  (a0)+,$2630(a1)
        move.l  (a0)+,$2652(a1)
        move.l  (a0)+,$268e(a1)
        move.l  (a0)+,$26b4(a1)
        move.l  (a0)+,$283e(a1)
        move.l  (a0)+,$2852(a1)
        move.l  (a0)+,$286a(a1)
        move.l  (a0)+,$2888(a1)
        move.l  (a0)+,$293e(a1)
        move.l  (a0)+,$296e(a1)
        move.l  (a0)+,$2998(a1)
        move.l  (a0)+,$29e4(a1)
        move.l  (a0)+,$2a14(a1)
        move.l  (a0)+,$3858(a1)
        move.l  (a0)+,$3868(a1)
        move.l  (a0)+,$3ad6(a1)
        move.l  (a0)+,$3ae6(a1)
        move.l  (a0)+,$3d54(a1)
        move.l  (a0)+,$3d64(a1)
        move.l  (a0)+,$3f1e(a1)
        move.l  (a0)+,$3f22(a1)
        move.w  V.l,$130c.w
        rts

.rs:    move.w  d2,d1                   ; a1 ring base, d2 head, d3 mask, d6 = window length + 3, a0 -> saved window
        and.w   #3,d1
        add.w   d6,d1
        lsr.w   #2,d1
        subq.w  #1,d1
        and.w   #$fffc,d2
.rc:    move.l  (a0)+,(a1,d2.w)
        addq.w  #4,d2
        and.w   d3,d2
        dbra    d1,.rc
        rts
