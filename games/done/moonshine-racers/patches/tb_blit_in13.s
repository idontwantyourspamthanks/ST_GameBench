; name: tb_blit_in13
; default: yes
; site: $38d8
; requires: tb_blit
; doc: Part of tb_blit: inner kernel pointer table ($38d8, nibble 13) for 3-part sprite caps/bases -> tb_blit ($B4D60).
        org     $38d8
        dc.l    $B4E60,$B4E70,$B4E80
