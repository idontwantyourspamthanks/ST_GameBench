; name: mw_credit
; default: yes
; version: 1.1
; site: $1088a
; orig: 61000112303c0000
; note: Release credit (st-game-speedup skill): a small, dim version line `v<VERSION> enhanced by dad_prg` on the Game Options screen
; note: (the main menu with PLAY and the option toggles; NOT the title picture, which stays untouched).
; note: THE ONE PLACE FOR THE RELEASE VERSION is the `; version:` header above: mw1patch.py substitutes it for the placeholder token in
; note: the string below, and `mw1patch.py version` prints it for tools/package.sh (zip names, PATCHES.TXT / README.TXT).
; note: Where: the screen is drawn by sub_01099e (the ONLY call is `bsr.w $1099e` at $1088a, inside the options loop that starts at
; note: $10884): it copies the picture $70000 into the draw buffer ($0(a6)), then draws the labels (MOUSE, STICK, KEYS, MORTARS,
; note: BOMBERS, TRAINING, PLAY, GAME OPTIONS) with the game's text routine sub_00a958 (a1 = string, a2 = glyph-index table $26323
; note: of the small font, $18(a6) = colour index, $16(a6) = y, $48(a6) = centre x; it centres the string and falls into sub_00a99c).
; note: Every toggle/mode click does `jsr (a0) ; bra $10884`, i.e. the whole screen is redrawn through that one call, so the text is
; note: redrawn each time with no extra hook.  The site is that `bsr.w $1099e` plus the `move.w #0,d0` behind it (8 bytes, nothing
; note: branches into the second half); the blob runs the original routine, draws the credit and ends with `move.w #0,d0`.
; note: Text: the game's own small font, two lines centred at x = 38 in the bottom-left corner, rows 180..197 (line 1 "v<VERSION>
; note: enhanced", line 2 "by dad_prg", pitch 9).  The picture's PLAY frame spans x 77..242 down to row 196; columns 0..76 and
; note: 243..319 are black from row 130 to 199 (checked on the decoded screen buffer), so the corner is empty.  The game's glyph
; note: drawer only sets pixels where the glyph has a bit (AND mask / OR colour), so the diff against the unpatched screen is
; note: exactly the glyph pixels.  Colour index 5 ($245 in this screen's palette, a muted slate blue; the labels use 2 = $157).
; note: The words $14..$49(a6) (the text routine's scratch fields: x, y, colour, glyph, width, flag, centre x) are saved and
; note: restored, so the game state after the call is that of the unpatched routine.
; note: Blob range: $B9000.. (free: patches use up to $B6840 and the site table starts at $BA000).
COLOUR  equ     5
CENTREX equ     38
LINE1Y  equ     178
LINE2Y  equ     187

        org     $1088a
        jsr     $b9000.l

        org     $b9000
        jsr     $1099e.l                ; the original `bsr.w $1099e`
        movem.l d0-d7/a0-a5,-(sp)
        lea     $14(a6),a0              ; save the text routine's scratch fields $14..$49(a6)
        lea     -$36(sp),sp
        movea.l sp,a1
        moveq   #26,d0
.sv:    move.w  (a0)+,(a1)+
        dbra    d0,.sv
        lea     $26323.l,a2             ; glyph-index table of the small font (as for the labels)
        move.w  #COLOUR,$18(a6)
        move.w  #CENTREX,$48(a6)
        move.w  #LINE1Y,$16(a6)
        lea     line1(pc),a1
        jsr     $a958.l
        move.w  #LINE2Y,$16(a6)
        lea     line2(pc),a1
        jsr     $a958.l
        lea     $14(a6),a0
        movea.l sp,a1
        moveq   #26,d0
.rs:    move.w  (a1)+,(a0)+
        dbra    d0,.rs
        lea     $36(sp),sp
        movem.l (sp)+,d0-d7/a0-a5
        move.w  #0,d0                   ; the instruction behind the original call
        rts
line1:  dc.b    "v@VERSION@ enhanced",0
line2:  dc.b    "by dad_prg",0
