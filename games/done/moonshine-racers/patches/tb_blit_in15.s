; name: tb_blit_in15
; default: yes
; site: $38ec
; requires: tb_blit
; doc: Part of tb_blit: inner kernel pointer table ($38ec, nibble 15) for 3-part sprite caps/bases -> tb_blit ($B4D90).
        org     $38ec
        dc.l    $B4E90,$B4EA0,$B4EB0
