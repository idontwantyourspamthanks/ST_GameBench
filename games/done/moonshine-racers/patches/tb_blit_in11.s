; name: tb_blit_in11
; default: yes
; site: $38c4
; requires: tb_blit
; doc: Part of tb_blit: inner kernel pointer table ($38c4, nibble 11) for 3-part sprite caps/bases -> tb_blit ($B4D30).
        org     $38c4
        dc.l    $B4E30,$B4E40,$B4E50
