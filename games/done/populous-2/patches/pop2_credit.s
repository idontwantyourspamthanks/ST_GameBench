; name: pop2_credit
; default: yes
; version: 1.0
; site: $15338
; orig: 4eb900001b9a
; doc: the main menu carries a small "v1.0 enhanced by dad_prg" line in the lower part of the slate panel
; note: Release credit (st-game-speedup "Release credit"): a tiny `v<VERSION> enhanced by dad_prg` on the MAIN MENU (the stone-framed
; note: POPULOUS II screen after the credits: CREATE YOUR DEITY / CONQUEST GAME / CUSTOM GAME / LOAD GAME), in the empty lower part of
; note: the dark slate panel, 3x5-pixel glyphs in a dim palette colour; nothing else on the screen changes.
; note: THE ONE PLACE FOR THE RELEASE VERSION is the `; version:` header above: pop2patch.py substitutes it for the placeholder token in
; note: the string below, and `pop2patch.py version` prints it for tools/package.sh (zip names, PATCHES.TXT / README.TXT).
; note: Where (disassembly of the unpacked game, work/notes/delivery.md): the main-menu routine $15304 loads the title picture into $54c80,
; note: copies it into BOTH screen buffers ($392e0 and $392dc, `jsr $21694` twice at $15314-$15332), then runs `jsr $1b9a`
; note: (pointer-hide counter -1) at $15338 and draws the menu box ($166d2).  The site is that `jsr $1b9a.l` (6 B); the blob draws
; note: into both buffers and ends in `jmp $1b9a.l`, so $1b9a returns to $1533e exactly as before.
; note: Own font (3x5, case-insensitive: 0-9 . _ a-z) so nothing depends on the game's text code; every pixel is set with bset/bclr in
; note: all four bit planes (colour index COL = 3, the dim tan the menu itself uses (palette word $0b32 there)), so only the glyph pixels change.
; note: Blob range: PB+$100.. (free: nothing else owns it).
COL     equ     3
X0      equ     112
Y0      equ     158
BLOB    equ     PB+$100

        org     $15338
        jsr     BLOB.l

        org     PB+$100
credit: movem.l d0-d7/a0-a6,-(sp)
        lea     $392dc.l,a5             ; the two screen buffer pointers ($392dc, $392e0)
        moveq   #1,d7
.buf:   movea.l (a5)+,a2
        lea     text(pc),a1
        move.w  #X0,d4
.chr:   moveq   #0,d0
        move.b  (a1)+,d0
        beq.s   .nxtbuf
        cmpi.b  #' ',d0
        beq.s   .adv
        cmpi.b  #'a',d0
        bhs.s   .let
        cmpi.b  #'.',d0
        beq.s   .dot
        cmpi.b  #'_',d0
        beq.s   .und
        subi.b  #'0',d0                 ; digit
        bra.s   .gl
.let:   subi.b  #'a'-12,d0
        bra.s   .gl
.dot:   moveq   #10,d0
        bra.s   .gl
.und:   moveq   #11,d0
.gl:    add.w   d0,d0
        lea     font(pc),a3
        move.w  (a3,d0.w),d5            ; 5 rows of 3 bits, row 0 in bits 15-13
        move.w  #Y0,d2
        moveq   #4,d3
.row:   rol.w   #3,d5
        move.w  d5,d0
        andi.w  #7,d0
        beq.s   .nr
        move.w  d4,d1
        btst    #2,d0
        beq.s   .c1
        bsr.s   plot
.c1:    addq.w  #1,d1
        btst    #1,d0
        beq.s   .c2
        bsr.s   plot
.c2:    addq.w  #1,d1
        btst    #0,d0
        beq.s   .nr
        bsr.s   plot
.nr:    addq.w  #1,d2
        dbra    d3,.row
.adv:   addq.w  #4,d4
        bra.s   .chr
.nxtbuf:dbra    d7,.buf
        movem.l (sp)+,d0-d7/a0-a6
        jmp     $1b9a.l                 ; the displaced call

; plot: a2 = buffer, d1 = x, d2 = y -> pixel (x,y) := colour COL.  Preserves everything but CCR.
plot:   movem.l d0/d6/a0,-(sp)
        move.w  d2,d0
        mulu    #160,d0
        lea     (a2,d0.l),a0
        move.w  d1,d0
        lsr.w   #3,d0                   ; byte column c = x>>3
        move.w  d0,d6
        andi.w  #1,d6
        lsr.w   #1,d0
        lsl.w   #3,d0
        add.w   d6,d0                   ; (c>>1)*8 + (c&1)
        adda.w  d0,a0
        moveq   #7,d0
        move.w  d1,d6
        andi.w  #7,d6
        sub.w   d6,d0                   ; bit 7-(x&7)
        ifne    COL&1
        bset    d0,(a0)
        else
        bclr    d0,(a0)
        endc
        ifne    COL&2
        bset    d0,2(a0)
        else
        bclr    d0,2(a0)
        endc
        ifne    COL&4
        bset    d0,4(a0)
        else
        bclr    d0,4(a0)
        endc
        ifne    COL&8
        bset    d0,6(a0)
        else
        bclr    d0,6(a0)
        endc
        movem.l (sp)+,d0/d6/a0
        rts

text:   dc.b    "v@VERSION@ enhanced by dad_prg",0
        even
font:   dc.w    $f6de,$592e,$e7ce,$e79e,$b792,$f39e,$f3de,$e524,$f7de,$f79e     ; 0-9
        dc.w    $0004,$000e                                                       ; . _
        dc.w    $57da,$d75c,$7246,$d6dc,$f34e,$f348,$72d6,$b7da,$e92e,$24d4      ; a-j
        dc.w    $b75a,$924e,$bfda,$d6da,$56d4,$d748,$56e6,$d75a,$711c,$e924      ; k-t
        dc.w    $b6de,$b6d4,$b7fa,$b55a,$b524,$e54e                               ; u-z
