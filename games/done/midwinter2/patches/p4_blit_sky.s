; name: p4_blit_sky
; default: no
; site: $1b996
; data: $b4bfe 2
; note: STE blitter sky/background fill (work/notes/blitter.md).  Sub $1b996 writes lines 58-199
;       of the back buffer ($67a6): per 160-byte line the first 8 bytes = 7fff7fff 7fff7fff,
;       the other 152 bytes = $ff (22,720 B, clears_blits.md).  The entry becomes jmp blob; the
;       blob replays the displaced 6 bytes (movem.l d0-d7/a0-a6,-(a7) + the opcode word of
;       movea.l $67a6.w,a6) and either returns to $1b99e (CPU path, original code) or blits.
;       Blit: pass A = words 4..79 of every line (76 w x 142 lines, OP=15 all ones, dst y-inc
;       10), pass B = words 0..3 of every line (4 w x 142, HOP=1 halftone $7fff, OP=3, y-inc 154).
;       Detection (first call, cached in FLAG $b4bfe: 0 unprobed / 1 blitter / 2 CPU path):
;       68000 CPU (excludes TT/Falcon), $ff8a3c readable (blitter present) and
;       $ff8e21 NOT readable (bus error; readable = Mega STE, 16 MHz CPU beats the 8 MHz blitter).
;       Bus-error probes: vector $8 temporarily replaced, handler discards the frame (a6 = sp).
HOG     equ     1                       ; 1 = HOG mode, 0 = non-HOG (shared bus), poll between passes
FLAG    equ     $b4bfe

        org     $1b996
        jmp     $b4700.l

        org     $b4700
sky:    movem.l d0-d7/a0-a6,-(a7)       ; displaced
        move.b  FLAG.l,d0
        beq.s   probe
        subq.b  #1,d0
        bne.s   cpu
        bra.s   blit

probe:  move.b  #2,FLAG.l               ; assume CPU path until proven otherwise
        moveq   #1,d0                   ; 68000 vs 68020+: the 68000 ignores the brief-extension
        suba.l  a0,a0                   ; scale bits, so lea (0,a0,d0.w*2),a1 gives 1 on a 68000
        dc.w    $43f0,$0200             ; (2 on 68020/030 = TT, Falcon)
        cmpa.w  #1,a1
        bne.s   cpu
        move.l  $8.w,d7                 ; saved bus-error vector
        movea.l a7,a6
        lea     .be(pc),a2
        move.l  a2,$8.w
        moveq   #0,d6
        tst.b   $ffff8a3c.l             ; blitter ctrl: bus error -> no blitter (d6 = 0)
        moveq   #1,d6
        tst.b   $ffff8e21.l             ; MegaSTE cache/CPU reg: bus error -> plain STE (d6 = 1)
        moveq   #2,d6                   ; readable -> Mega STE
.be:    movea.l a6,a7
        move.l  d7,$8.w
        cmpi.b  #1,d6
        bne.s   cpu
        move.b  #1,FLAG.l
        bra.s   blit

cpu:    movea.l $67a6.w,a6              ; displaced (second half), then the original body
        jmp     $1b99e.l

blit:   lea     $ffff8a00.l,a0
        movea.l $67a6.w,a1
        lea     $2440(a1),a1            ; line 58
        moveq   #-1,d0
        move.w  d0,$28(a0)              ; endmask1-3 = $ffff
        move.w  d0,$2a(a0)
        move.w  d0,$2c(a0)
        move.w  #2,$2e(a0)              ; dst x-inc
        clr.b   $3d(a0)                 ; skew 0, no FXSR/NFSR
        move.l  #$7fff7fff,d1          ; halftone RAM = $7fff x16 (pass B; not touched while busy)
        move.l  d1,(a0)+
        move.l  d1,(a0)+
        move.l  d1,(a0)+
        move.l  d1,(a0)+
        move.l  d1,(a0)+
        move.l  d1,(a0)+
        move.l  d1,(a0)+
        move.l  d1,(a0)+
        lea     -32(a0),a0
        ; pass A: words 4..79
        lea     8(a1),a2
        move.l  a2,$32(a0)
        move.w  #10,$30(a0)             ; 160 - 75*2
        move.w  #76,$36(a0)
        move.w  #142,$38(a0)
        move.w  #$000f,$3a(a0)          ; HOP=0 OP=15
        move.b  #$80+$40*HOG,$3c(a0)    ; start
        IF HOG=0
.w1:    btst    #7,$3c(a0)
        bne.s   .w1
        ENDC
        ; pass B: words 0..3
        move.l  a1,$32(a0)
        move.w  #154,$30(a0)            ; 160 - 3*2
        move.w  #4,$36(a0)
        move.w  #142,$38(a0)
        move.w  #$0103,$3a(a0)          ; HOP=1 OP=3
        move.b  #$80+$40*HOG,$3c(a0)
        IF HOG=0
.w2:    btst    #7,$3c(a0)
        bne.s   .w2
        ENDC
        movem.l (a7)+,d0-d7/a0-a6
        rts
