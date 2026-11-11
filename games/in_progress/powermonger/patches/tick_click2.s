; name: tick_click2
; default: yes
; site: $1354
; orig: 0002df70
; note: P2 (needs tick_head, tick_click). Second latch site of the click lifetime, see tick_click.
        org     $1354
        dc.l    $b8a20
