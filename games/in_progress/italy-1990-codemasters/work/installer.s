
                org     $f8000
install_start:
                ; Copy patch.bin -> $3a000
                lea     patch_payload(pc),a0
                lea     $3a000.l,a1
                move.w  #4091,d0
.cp:            move.w  (a0)+,(a1)+
                dbra    d0,.cp

                ; Apply site table: [addr.l, len.w, bytes..., pad-to-even], 0.l terminator
                lea     site_table(pc),a0
.sloop:         move.l  (a0)+,d0
                beq.s   .sdone
                movea.l d0,a1
                move.w  (a0)+,d1
                move.w  d1,d2
                subq.w  #1,d1
.bcp:           move.b  (a0)+,(a1)+
                dbra    d1,.bcp
                btst    #0,d2
                beq.s   .sloop
                addq.l  #1,a0
                bra.s   .sloop
.sdone:
                jmp     $400.l

                even
site_table:
                incbin  "/home/ryan/Code/AtariST/gamebench/games/in_progress/italy-1990-codemasters/work/site_table.bin"
                even
patch_payload:
                incbin  "/home/ryan/Code/AtariST/gamebench/games/in_progress/italy-1990-codemasters/work/patch.bin"
