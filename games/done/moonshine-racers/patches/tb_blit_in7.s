; name: tb_blit_in7
; default: yes
; site: $38b0
; requires: tb_blit
; doc: Part of tb_blit: inner kernel pointer table ($38b0, nibble 7) for 3-part sprite caps/bases -> tb_blit ($B4D00).
        org     $38b0
        dc.l    $B4E00,$B4E10,$B4E20
