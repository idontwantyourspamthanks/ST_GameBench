; name: p8_spr8
; default: yes
; stage: 2
; site: $11fd8
; orig: 0c41000867000058
; data: $ca800 9216
; note: pre-shifted sprite cache for 8x11 masked small sprites (SPRITE8.DAT at $33000..$37c7b, routine $11f82..$120e8).
;       Site $11fd8 is right after Y clipping, screen address calculation and `andi.w #$f,d1`:
;         a0 = screen address (16-px group aligned), a1 = sprite rows (5 B/row: mask.b, p0..p3.b), d1 = shift s (0..15), d2 = rows - 1 (0..10).
;       Cache at $ca800..$ccbff (9216 B, zero-filled, 0 disk bytes, inside HD_WINDOW): 8 sets x 4 ways = 32 slots x 272 B = 8704 B + tags.
;       Lazy init guarded by MAGIC 'PS80'. Falls back to original code for a1 outside SPRITE8 or d2 > 10. Preserves a2-a6.
HDR     equ     $ca800
TAGS    equ     $ca810                  ; 8 sets x (2 B rr + 4 x 12 B entries) = 8 x 50 = 400 B ($ca810..$ca99f)
SLOTS   equ     $caa00                  ; 32 x 272 B = 8704 B ($caa00..$ccbff)
SHEET0  equ     $33000
SHEET1  equ     $37c7c
MAGIC   equ     $50533830               ; 'PS80'

        org     $11fd8
        jmp     $da100.l
        nop

        org     $da100
spr8:   cmpi.w  #10,d2
        bhi.w   .orig
        cmpa.l  #SHEET0,a1
        bcs.w   .orig
        cmpa.l  #SHEET1,a1
        bcc.w   .orig
        movem.l a2-a3,-(a7)
        cmpi.l  #MAGIC,HDR.l
        beq.s   .ini
        bsr.w   init8
.ini:   move.l  a1,d0
        lsr.l   #2,d0
        add.w   d1,d0
        move.w  d0,d3
        lsr.w   #3,d3
        eor.w   d3,d0
        andi.w  #7,d0                   ; set 0..7
        mulu.w  #50,d0                  ; 2 + 4*12
        lea     TAGS.l,a2
        adda.w  d0,a2
        lea     2(a2),a3
        moveq   #3,d3
.w:     cmpa.l  (a3),a1
        bne.s   .n
        cmp.w   8(a3),d1
        beq.s   .found
.n:     lea     12(a3),a3
        dbra    d3,.w
        ; miss: round-robin victim
        move.w  (a2),d3
        move.w  d3,d4
        addq.w  #1,d4
        andi.w  #3,d4
        move.w  d4,(a2)
        mulu.w  #12,d3
        lea     2(a2),a3
        adda.w  d3,a3
        move.l  a1,(a3)
        move.w  d1,8(a3)
        clr.w   10(a3)                  ; rows built = 0
.found: move.w  d2,d4
        addq.w  #1,d4                   ; needed rows (1..11)
        cmp.w   10(a3),d4
        bls.s   .draw
        move.w  d4,10(a3)
        bsr.w   build8
.draw:  movea.l 4(a3),a3
        move.w  d2,d4                   ; dbra count = rows - 1
        cmpi.w  #8,d1
        bgt.s   .r2
.r1:    movem.l (a3)+,d0-d2
        move.l  (a0),d3
        and.l   d0,d3
        or.l    d1,d3
        move.l  d3,(a0)+
        move.l  (a0),d3
        and.l   d0,d3
        or.l    d2,d3
        move.l  d3,(a0)
        lea     156(a0),a0
        dbra    d4,.r1
        movem.l (a7)+,a2-a3
        rts
.r2:    movem.l (a3)+,d0-d2
        move.l  (a0),d3
        and.l   d0,d3
        or.l    d1,d3
        move.l  d3,(a0)+
        move.l  (a0),d3
        and.l   d0,d3
        or.l    d2,d3
        move.l  d3,(a0)+
        movem.l (a3)+,d0-d2
        move.l  (a0),d3
        and.l   d0,d3
        or.l    d1,d3
        move.l  d3,(a0)+
        move.l  (a0),d3
        and.l   d0,d3
        or.l    d2,d3
        move.l  d3,(a0)
        lea     148(a0),a0
        dbra    d4,.r2
        movem.l (a7)+,a2-a3
        rts
.orig:  cmpi.w  #8,d1
        beq.s   .eq8
        jmp     $11fe0.l
.eq8:   jmp     $12036.l

build8: movem.l d1-d2/a1/a2,-(a7)
        movea.l 4(a3),a2
        subq.w  #1,d4
        cmpi.w  #8,d1
        bgt.s   .b2
        moveq   #8,d0
        sub.w   d1,d0
.b1:    moveq   #-1,d5
        move.b  (a1)+,d5
        rol.w   d0,d5
        move.w  d5,d6
        swap    d6
        move.w  d5,d6
        move.l  d6,(a2)+
        clr.w   d5
        move.b  (a1)+,d5
        rol.w   d0,d5
        swap    d5
        clr.w   d5
        move.b  (a1)+,d5
        rol.w   d0,d5
        move.l  d5,(a2)+
        clr.w   d5
        move.b  (a1)+,d5
        rol.w   d0,d5
        swap    d5
        clr.w   d5
        move.b  (a1)+,d5
        rol.w   d0,d5
        move.l  d5,(a2)+
        dbra    d4,.b1
        movem.l (a7)+,d1-d2/a1/a2
        rts
.b2:    move.w  d1,d0
        subq.w  #8,d0
.b2l:   moveq   #-1,d5
        move.b  (a1)+,d5
        ror.w   d0,d5
        move.w  d5,d6
        ori.w   #$ff00,d6
        move.w  d6,d7
        swap    d7
        move.w  d6,d7
        move.l  d7,(a2)+
        move.w  d5,d3
        ori.w   #$00ff,d3
        clr.w   d5
        move.b  (a1)+,d5
        ror.w   d0,d5
        clr.w   d6
        move.b  (a1)+,d6
        ror.w   d0,d6
        move.w  d5,d7
        andi.w  #$00ff,d7
        swap    d7
        move.w  d6,d7
        andi.w  #$00ff,d7
        move.l  d7,(a2)+
        andi.w  #$ff00,d5
        swap    d5
        move.w  d6,d5
        andi.w  #$ff00,d5
        clr.w   d6
        move.b  (a1)+,d6
        ror.w   d0,d6
        clr.w   d7
        move.b  (a1)+,d7
        ror.w   d0,d7
        move.w  d6,d2
        andi.w  #$00ff,d2
        swap    d2
        move.w  d7,d2
        andi.w  #$00ff,d2
        move.l  d2,(a2)+
        move.w  d3,d2
        swap    d2
        move.w  d3,d2
        move.l  d2,(a2)+
        move.l  d5,(a2)+
        andi.w  #$ff00,d6
        swap    d6
        move.w  d7,d6
        andi.w  #$ff00,d6
        move.l  d6,(a2)+
        dbra    d4,.b2l
        movem.l (a7)+,d1-d2/a1/a2
        rts

init8:  lea     TAGS.l,a2
        lea     SLOTS.l,a3
        moveq   #7,d3
.s:     clr.w   (a2)+                   ; rr
        moveq   #3,d4
.e:     clr.l   (a2)+                   ; tag
        move.l  a3,(a2)+                ; slot ptr
        clr.w   (a2)+                   ; s
        clr.w   (a2)+                   ; rows
        lea     272(a3),a3
        dbra    d4,.e
        dbra    d3,.s
        move.l  #MAGIC,HDR.l
        rts
