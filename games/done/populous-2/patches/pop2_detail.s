; name: pop2_detail
; default: yes
; site: $1d14
; orig: 13c0000392ec
; data: PB+$18e0 16
; note: F7 Detail Level toggle (High / Low) for Populous 2 (F1-F6 are already used by Populous 2's
;       6 effect categories, so F7 ($41) sits right next to them).
;       Data at PB+$18e0: +0 DETAIL.w (0 = High, 1 = Low), +2 BANNER.l (VBL stamp + 1 for 2 s sky flash).
;       In Low Detail: throttles minimap per-peep dot plotting (pop2_tick_dot_a) to every 4th turn.
;       100% pixel-identical in High Detail mode (default).  Blob PB+$1800.

D       equ     PB+$18e0

        org     $1d14
        jsr     (PB+$1800).l

        org     PB+$1800
det_k:  move.b  d0,$392ec.l             ; displaced store
        cmp.b   #$41,d0                 ; F7?
        bne.s   .r
        cmpi.w  #8,$39766.l             ; normal map view?
        bne.s   .r
        eor.w   #1,D.l
        move.l  $392d8.l,d1
        addq.l  #1,d1
        move.l  d1,D+2.l                ; 2 s sky-strip flash stamp + 1
        clr.b   $392ec.l                ; consume F7
.r:     rts
