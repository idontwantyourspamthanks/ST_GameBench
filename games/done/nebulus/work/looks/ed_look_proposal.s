; DESIGN SKETCH (not merged; patches/ed_editor.s is not touched): per-level colour + enemy-eye set from the record's flags.b.
;   flags.b bits 0-3 = eye-disc design override: 0 = follow the base tower, 1..4 = design 0..3 (the game has 4: tower&3)
;   flags.b bits 4-7 = colour override: 0 = follow the base tower, 1..8 = the palette + raster colours of tower 1..8
; Assembled standalone only to measure the bytes (vasmm68k_mot -Fbin -m68000 -no-opt).  Externals are stubbed.
RS      equ     $77c80
rsFlg   equ     50                      ; word, free in RS (rsLast = 48, rsTosP = 52)
rsMis   equ     12
rsTow   equ     14
RSV     equ     RS-$77cc0
vDirty  equ     162
        org     $76d40
cur_rec: rts                            ; stub: a0 = record of the level being played / 0 (real one: ed_editor.s, CODE1)
c_ldone: rts                            ; stub

; ---- game-side hooks (3 sites, 6 B each: the original `move.w $3390c.l,d0` is replaced by `jsr ed_xxx.l`)
; site $363a4 (sub_03636e: eye sprite set = tower&3 -> $54aba+(d0&3)*$a00); a0 live, d0/d1 dead
ed_eye: moveq   #0,d1
        bra.s   lk
; sites $3522e (sub_035228: 16 palette words) and $3dc1e (sub_0351cc: 4 raster colours): d0 out = tower index whose colours are used; a0 live (palette site)
ed_col: moveq   #4,d1
lk:     move.l  a0,-(a7)
        bsr     cur_rec                 ; a0 = custom record or 0 (original tower / no store)
        move.l  a0,d0
        beq.s   .base
        move.b  3(a0),d0                ; flags
        lsr.b   d1,d0
        and.w   #15,d0
        beq.s   .base
        move.l  (a7)+,a0
        subq.w  #1,d0
        rts
.base:  move.w  $3390c.l,d0
        move.l  (a7)+,a0
        rts

; ---- editor side
; menu items (tables block): 4,17,'Colours: next',0 / 4,18..'Enemies: next',0 ; cmds += c_col, c_eye
c_eye:  moveq   #0,d1
        moveq   #5,d2
        bra.s   cyc
c_col:  moveq   #4,d1
        moveq   #9,d2
cyc:    move.w  RSV+rsFlg(a5),d0
        move.w  d0,d3
        lsr.w   d1,d3
        and.w   #15,d3
        addq.w  #1,d3
        cmp.w   d2,d3
        blo.s   .k
        moveq   #0,d3
.k:     move.w  #$f,d4
        lsl.w   d1,d4
        not.w   d4
        and.w   d4,d0
        lsl.w   d1,d3
        or.w    d3,d0
        move.w  d0,RSV+rsFlg(a5)
        jmp     c_ldone                 ; marks dirty, closes the menu, redraws (shared tail of c_look/c_mis)
; commit: replace `clr.b 3(a2)` (2 B... 4 B) by  `move.w RSV+rsFlg(a5),d0 / move.b d0,3(a2)`  (+4 B)
; lv_edit: after `move.b 1(a0),d0 / move.w d0,rsTow`:  `move.b 3(a0),d0 / move.w d0,RSV+rsFlg(a5)`  (+8 B)
; c_newlvl: `clr.w RSV+rsFlg(a5)` (+4 B)
        end
