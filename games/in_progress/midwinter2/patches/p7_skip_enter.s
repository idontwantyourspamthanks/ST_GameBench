; name: p7_skip_enter
; default: yes
; site: $28cf6
; orig: 33fc000200018124
; phase: boot
; note: P7 item 5(a), part 4/7 (work/notes/p7_static_skip.md).  Common tail of the 3D-view (re)entry $28cc0
;       (both the path through the cockpit encoder $28cee and the `bmi.b $28cf6` path for types without a
;       cockpit picture): the screen buffers and the cockpit list may hold anything after a screen change, so
;       forget the per-buffer render snapshots (VAL[] of p7_skip_render).
;       Displaces `move.w #$2,$18124.l`; rejoins at $28cfe.
D       equ     $b6000
VAL     equ     D+$00
NINV    equ     D+$1c

        org     $28cf6
        jmp     $b7cc0.l
        nop

        org     $b7cc0
        clr.l   VAL.l
        addq.l  #1,NINV.l
        move.w  #$2,$18124.l            ; displaced
        jmp     $28cfe.l
