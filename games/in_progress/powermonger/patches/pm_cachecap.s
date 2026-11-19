; name: pm_cachecap
; default: yes
; stage: 2
; site: $e000
; orig: 22790002c1ba
; note: Retire / win / lose black screen (work/notes/retire.md).  The game's resource loader ($df52) CACHES every decompressed resource it loads
;       in RAM: a bump allocator, cursor [$2c1ba], that starts at $80000 (set at $1118 iff the probe write at $80000 finds RAM; a 512 KB machine has
;       cursor 0 = no cache) and grows upwards with NO upper bound (the copy loop is $e02c, the cursor store $e032).  By the map view the cursor is
;       at $b74f4 (resources 10, 11, 1, 8 = $374f4 B); the LOSE / WIN picture (resource 14 / 15, $7d00 B) is cached next, at $b74f4..$bf1f4, which
;       is on top of our payload ($b8000..: core, tick, p4 cache, p7 ... ), so the first VBL after that runs trampled code.
;       Fix: `movea.l $2c1ba.l,a1` (the first instruction of the cache step, a0 = the decompressed data, d2 = its size) becomes a call that loads
;       the cursor and, if this resource would end above $b8000, returns a1 = 0: the following `cmpa.l #0,a1 / beq $e038` then skips the cache
;       copy, exactly as on a 512 KB machine (e040[res] stays 0, so the next use loads the resource from the disk again; the picture itself is
;       already in its destination buffer).  Only resources that do not fit are not cached (about the first 2.8 KB are all that is left below
;       $b8000, so in practice: the win / lose / end pictures).
CAPLIM  equ     $b8000
        org     $e000
        jsr     $dc100.l

        org     $dc100
ccap:   movea.l $2c1ba.l,a1             ; the displaced instruction: cursor (0 = no cache)
        move.l  a1,d0
        beq.s   .ret                    ; 0: the game's own skip follows
        add.l   d2,d0                   ; end of this resource's copy
        cmp.l   #CAPLIM,d0
        bls.s   .ret                    ; fits below the payload: cache it as before
        suba.l  a1,a1                   ; does not fit: a1 = 0 -> `cmpa.l #0,a1 / beq $e038` skips the copy
.ret:   rts
