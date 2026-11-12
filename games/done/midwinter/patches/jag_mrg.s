; name: jag_mrg
; default: yes
; site: $65e2
; orig: 34390002c328
; note: Jaguar pad support, part 2 of 4 (see jag_vbl; work/notes/jagpad.md).  $65c0 (VBL, every VBL) turns the latched IKBD joystick byte
;       into the held vector $24f98/$24f9c: `move.w $2c328.l,d2` (6 bytes, only on a new byte) becomes the same load OR-ed with PADJ
;       (the pad directions in the same bit layout, 0 without a pad / outside joystick mode).  $2c328 itself is never modified, so the
;       real stick and the pad both work.  Without jag_vbl PADJ stays 0 and nothing changes.
        org     $65e2
        jsr     $b6c00.l

        org     $b6c00
        move.w  $2c328.l,d2             ; displaced
        or.b    $b6bf1.l,d2             ; PADJ (jag_vbl)
        rts
