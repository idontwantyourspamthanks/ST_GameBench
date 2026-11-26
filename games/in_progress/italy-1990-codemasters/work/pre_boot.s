
                org     $547a4
pre_boot:
                ; 1. Copy installer_bin -> $fe000 (PC-relative!)
                lea     pre_boot(pc),a0
                suba.l  #8734,a0
                lea     $f8000.l,a1
                move.w  #4366,d0
.cp_inst:       move.w  (a0)+,(a1)+
                dbra    d0,.cp_inst

                ; 2. Copy post_menu_hook -> $7fd60 (36 words = 72 bytes)
                lea     post_menu_hook(pc),a0
                lea     $7fd60.l,a1
                moveq   #35,d0
.cp_pmh:        move.w  (a0)+,(a1)+
                dbra    d0,.cp_pmh

                ; 3. Patch $7fd4e (copied $524 `jmp $400.l`) -> `jmp $7fd60.l`
                move.l  #$4ef90007,$7fd4e.l
                move.w  #$fd60,$7fd52.l

                ; 4. Jump to $7fd00 (original menu+payload copier!)
                jmp     $7fd00.l

post_menu_hook:
                ; Runs at $7fd60 AFTER menu is copied to $400..$12000!
                ; 1. Skip 'PLEASE SELECT F1 ST / F2 STE' at $e20 -> auto-select STE (`st.b $1198.l; rts`)
                move.l  #$50f90000,$e20.l
                move.l  #$11984e75,$e24.l
                ; 2. Instant menu fades & transitions: RTS at $54e + cut $d5c & $bb8 waits!
                move.w  #$4e75,$54e.l
                move.w  #$7001,$d5c.l
                move.w  #$0008,$bb8.l
                ; 3. Patch $2ba8 (`jmp $400.l` after 11-A-Side Soccer unpacks) -> `jmp $f8000.l`
                move.l  #$4ef9000f,$2ba8.l
                move.w  #$8000,$2bac.l
                jmp     $400.l
