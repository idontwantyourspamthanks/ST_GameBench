; name: pm_cachecap
; default: yes
; site: $e3f2
; orig: 22790002cfda
; note: the resource loader ($e344) CACHES every unpacked resource it loads in RAM: a bump allocator, cursor [$2cfda], that starts at $80000 (set at
;       $5ee iff the probe write at $80000 finds RAM; a 512 KB machine has cursor 0 = no cache) and grows upwards with NO upper bound (copy loop $e41e, cursor
;       store $e424).  By the map view the cursor is at $9fc58 and after LOSE and WIN pictures were seen it is $af658 (work/notes/memory_plan.md 2.2, 2.3).  The
;       HIGH area $b0000-$f6fff holds this port's big buffers (third screen, slope table, DMA staging, interpolation lists, sprite cache, HD swap buffer), so a
;       resource that would end above it must not be cached.  The cache's own end can only pass $af658 by a resource the game never loaded in any session
;       tested: END_PIC1 / END (campaign end, resources 12 / 13) and BITMAP (7).  Normal play therefore costs no extra disk read (gate M3a).
;       Site: `movea.l $2cfda.l,a1` (the first instruction of the cache step; a0 = the unpacked data, d2 = its size) becomes a call that loads the cursor and, if
;       this resource would end above CAPLIM, returns a1 = 0: the following `cmpa.l #0,a1 / beq $e42a` skips the cache copy, exactly as on a 512 KB machine
;       (cache pointer [$e432 + 4 * n] stays 0, so the next use loads the resource from the disk again; the picture is already in its destination).
;       CAPLIM = HI_BASE of tools/wwpatch.py (the build refuses a different value).
CAPLIM  equ     $b0000
        org     $e3f2
        jsr     $75800.l

        org     $75800
ccap:   movea.l $2cfda.l,a1             ; the displaced instruction: cursor (0 = no cache)
        move.l  a1,d0
        beq.s   .ret                    ; 0: the game's own skip follows
        add.l   d2,d0                   ; end of this resource's copy
        cmp.l   #CAPLIM,d0
        bls.s   .ret                    ; fits below the HIGH area: cache it as before
        suba.l  a1,a1                   ; does not fit: a1 = 0 -> `cmpa.l #0,a1 / beq $e42a` skips the copy
.ret:   rts
