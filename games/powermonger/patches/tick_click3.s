; name: tick_click3
; default: no
; site: $1373e
; orig: 0002df70
; note: P2 (needs tick_head, tick_click). The loop's click-expiry test `move.l $2df70.l,d0 ; cmp.l $2df74.l,d0` at $1373c, see tick_click.
        org     $1373e
        dc.l    $b8a20
