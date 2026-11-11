; name: mw2_credit
; default: yes
; version: 1.3
; site: $1f5f0
; orig: 3d7c00a0000e
; phase: boot
; note: Release credit (st-game-speedup skill): a small, dim version line `v<VERSION> enhanced by dad_prg` at the BOTTOM of the
; note: orange MIDWINTER II logo screen (the one that is followed by "Insert Graphics Disk / press any key" on a floppy boot, and
; note: that stays up while the intro files load on the HD build).  The logo art, the palette and the prompt are untouched.
; note: THE ONE PLACE FOR THE RELEASE VERSION is the `; version:` header above: mw2patch.py substitutes it for the placeholder
; note: token in the string below, and `mw2patch.py version` prints it for tools/package.sh (zip names, PATCHES.TXT / README.TXT).
; note: Where (disassembly of FFA file 9, work/notes/credit.md): after the FLAMES OF FREEDOM title (drawn by the boot stub) the game
; note: starts at $312a8; sub_01f4fc (called from $2c56a) draws the logo in the two screen buffers, copies the displayed one
; note: ($4(a6) = $70000) into the draw buffer ((a6) = $60000) at $1f5dc and then, at $1f5ea..$1f61c, draws the prompt lines with the
; note: game's text routine ($4ed0.w -> $2abd2) into the draw buffer and flips ($4f36.w) to show it.  The same code runs on floppy
; note: and HD (the HD build differs only by PP's bytes at $1f5ea and $1f636: no stub sector read, no key wait, so the prompt
; note: is on screen for no time at all and the BARE logo remains up, buffer $70000, while the intro files load).  Both builds
; note: therefore need the credit in BOTH buffers: it is drawn into the draw buffer and the text rows are copied to the other one
; note: (the two buffers are identical at this point: sub_2a474 just copied one to the other).
; note: Site: the `move.w #$a0,$e(a6)` at $1f5f0, which starts the prompt text and sits after PP's $1f5ea patch (a different 6
; note: bytes).  $1f5f0 lies inside the FFB f1 overlay range ($18d96-$210b2), which is only loaded much later, so this is a
; note: BOOT site; the in-game dump holds the overlay there, tools/mw2patch.py compares it with work/dumps/ram_boot_hd1mb.bin
; note: (RAM at game entry of an unpatched HD boot) instead.  The blob replays the displaced instruction at its end.
; note: Text: the game's own font 1 (the prompt's), centred at x = 160, glyph box rows 188..196 (caps 7 rows high, descenders to
; note: row +8); the prompt's last glyph row is 178.  Colour index 2 ($630, the dark amber of the logo's rim; the palette is
; note: 0 black, 1 $500, 2 $630, 3 $740, 4 $750, 5 $762, 15 white).  The glyph drawer only sets glyph pixels, so the diff to the
; note: unpatched screen is exactly the text.  The text routine's scratch words $0e..$49(a6) and $11e..$126(a6) are saved and
; note: restored, so the game state after the hook is that of the unpatched code.
; note: Blob range: $B9000.. (free: p7_skip_* use up to $B7D5F; test_blob16k, default no, owns $B6000-$B9FFF).
COLOUR  equ     2
CREDITY equ     188
ROWS    equ     10

        org     $1f5f0
        jsr     $b9000.l

        org     $b9000
        movem.l d0-d7/a0-a6,-(sp)
        lea     $770e.w,a6
        lea     -70(sp),sp              ; save $0e..$49 (30 words) and $11e..$126 (5 words)
        lea     $e(a6),a0
        movea.l sp,a1
        moveq   #29,d0
.sv1:   move.w  (a0)+,(a1)+
        dbra    d0,.sv1
        lea     $11e(a6),a0
        moveq   #4,d0
.sv2:   move.w  (a0)+,(a1)+
        dbra    d0,.sv2
        move.w  #1,$11e(a6)             ; the prompt's font
        clr.w   $120(a6)                ; text-mode flags the text routine resets itself
        clr.w   $122(a6)
        clr.w   $124(a6)
        move.w  #160,$e(a6)             ; centre x (string code 5 centres on it)
        move.w  #CREDITY,$10(a6)
        lea     text(pc),a1
        jsr     $4ed0.w
        movea.l (a6),a0                 ; the draw buffer now holds the text: copy those rows to the other buffer
        movea.l 4(a6),a1
        adda.w  #CREDITY*160,a0
        adda.w  #CREDITY*160,a1
        move.w  #ROWS*40-1,d0
.cp:    move.l  (a0)+,(a1)+
        dbra    d0,.cp
        movea.l sp,a0
        lea     $e(a6),a1
        moveq   #29,d0
.rs1:   move.w  (a0)+,(a1)+
        dbra    d0,.rs1
        lea     $11e(a6),a1
        moveq   #4,d0
.rs2:   move.w  (a0)+,(a1)+
        dbra    d0,.rs2
        lea     70(sp),sp
        movem.l (sp)+,d0-d7/a0-a6
        move.w  #$a0,$e(a6)             ; the displaced instruction
        rts
text:   dc.b    1,COLOUR,5,"v@VERSION@ enhanced by dad_prg",0
        even
