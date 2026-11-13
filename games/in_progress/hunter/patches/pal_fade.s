; name: pal_fade
; default: no
; site: $67fc
; orig: 3002e75a024207774e75
; requires: pal_load
; note: STE 4096-colour palette, part 1 of 2 (work/notes/visuals.md).  The game's palettes are the Amiga's 12-bit ones; the fade
; note: code keeps every gun as a 4.4 fixed-point byte and $67ea packs the three high nibbles into d2 = $R0BG.  The Amiga does `rol.w #4`
; note: (-> $0RGB); the ST does `rol.w #3 / andi.w #$777` at $67fe = ($0RGB >> 1) & $777: the low bit of every gun is thrown away.
; note: On STE-class palette hardware (FLAGS bit0: STE, Mega STE, TT, Falcon) this patch writes the STE form instead:
; note: ((c >> 1) & $777) | ((c & $111) << 3), i.e. all 4 bits per gun.  A plain ST / Mega ST takes the original two instructions.
; note: d0 = the packed value before the rotate, as in the original (no caller reads it; kept anyway).  d2.w = result.  Flags are not used
; note: by the two callers ($67a6, $67da).
FLAGS   equ     $8bff0
PAL     equ     $8c014

        org     $67fc
        jmp     PAL.l                   ; replaces `move.w d2,d0 / rol.w #3,d2 / andi.w #$777,d2 / rts` (10 B)
        nop
        nop

        org     $8c014
pal_fade:
        move.w  d2,d0                   ; original
        btst    #0,FLAGS+3.l            ; STE-class palette?
        beq.s   .st
        rol.w   #4,d2                   ; $0RGB, the Amiga's value
        move.w  d2,-(sp)
        andi.w  #$111,d2                ; the low bit of each gun ...
        lsl.w   #3,d2                   ; ... is bit 3 of the STE nibble
        lsr.w   (sp)
        andi.w  #$777,(sp)              ; the upper three bits, as on the ST
        or.w    (sp)+,d2
        rts
.st:    rol.w   #3,d2                   ; the original instructions
        andi.w  #$777,d2
        rts
