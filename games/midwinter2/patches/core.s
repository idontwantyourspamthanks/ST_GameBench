; core.s — MW2 patch delivery mechanism (always installed by mw2patch.py).
; Assembled into the $B3000 image in three fixed-org segments.
;   $B3000 trampoline: entered from PP's patcher tail (RAM $594, see README), or
;            for the floppy build (`build --floppy`, assembled with FLOPPY equ 1) from
;            the FFA boot stub's stage-1 loader. Replays the PP patch displaced from
;            $594 (HD build only), verifies+applies all
;            phase=boot sites, writes 'MWPO'/'MWPF' to $B2FF8, jmp $3104.
;   $B3070 hookexit:   entered from the $2789A splice (sub_2783E success exit);
;            restores exactly like the original exit, then runs apply.
;   $B3090 apply:      applies phase=deferred sites whose address range is
;            covered by the file load that just finished ([$6918],[$6914]).
;            Idempotent: orig bytes -> apply; new bytes -> already done;
;            anything else -> 'MWPF' marker, site left untouched.
; Site table at $BA000-$BAFFF (4 KB): entries {addr.l len.w phase.w orig.l new.l}, addr 0 ends.
TABLE   equ $ba000
MARKER  equ $b2ff8
apply   equ $b3090

        org     $b3000
trampoline:
        ; PP's security-check bypass (loading.md 6). The HD build displaced it
        ; from $594 and the floppy build never runs PP's patcher; on both
        ; media this bypass is wanted, so it is applied unconditionally.
        move.w  #$6002,$2c574.l
        movem.l d0-d7/a0-a6,-(a7)
        move.w  sr,-(a7)                ; keep flags/mode exactly as the patcher left them
        move.l  #'MWPF',MARKER.l        ; preset failure marker
        lea     TABLE.l,a0
.tloop: move.l  (a0)+,d0                ; site addr; 0 = end of table
        beq.s   .tok
        move.w  (a0)+,d1                ; length
        move.w  (a0)+,d2                ; phase: 0 boot / 1 deferred
        move.l  (a0)+,a1                ; orig bytes
        move.l  (a0)+,a2                ; new bytes
        tst.w   d2
        bne.s   .tloop                  ; deferred sites: load hook handles them
        movea.l d0,a3
        move.w  d1,d3
        subq.w  #1,d3
.tv:    move.b  (a1)+,d4
        cmp.b   (a3)+,d4
        bne.s   .tfail
        dbra    d3,.tv
        movea.l d0,a3
        move.w  d1,d3
        subq.w  #1,d3
.ta:    move.b  (a2)+,(a3)+
        dbra    d3,.ta
        bra.s   .tloop
.tfail: move.w  (a7)+,sr
        movem.l (a7)+,d0-d7/a0-a6       ; mismatch: apply nothing, keep MWPF
        jmp     $3104.w
.tok:   move.l  #'MWPO',MARKER.l
        move.w  (a7)+,sr
        movem.l (a7)+,d0-d7/a0-a6
        jmp     $3104.w

        org     $b3070
hookexit:                               ; replaces 46df 31df 62f2 at $2789A
        movem.l d0-d7/a0-a6,-(a7)       ; work FIRST, still supervisor on the
        jsr     apply.l                 ; known ISP frame (saved sr may be user
        movem.l (a7)+,d0-d7/a0-a6       ; mode: restoring it swaps a7 to USP)
        move.w  (a7)+,sr                ; original exit sequence from here on
        move.w  (a7)+,$62f2.w
        movem.l (a7)+,d0-d7/a0-a6
        rts                             ; -> caller of sub_2783E

        org     $b3090
        move.l  $6918.w,d0              ; dest of the load that just finished
        move.l  $6914.w,d1              ; its length
        add.l   d0,d1                   ; d1 = end
        lea     TABLE.l,a0
.aloop: move.l  (a0)+,d2                ; addr; 0 = end
        beq.s   .adone
        move.w  (a0)+,d3                ; len
        move.w  (a0)+,d4                ; phase
        move.l  (a0)+,a1                ; orig
        move.l  (a0)+,a2                ; new
        cmpi.w  #1,d4
        bne.s   .aloop                  ; boot site: not ours
        cmp.l   d0,d2
        blt.s   .aloop                  ; below load range
        move.l  d2,d5
        add.l   d3,d5
        cmp.l   d1,d5
        bgt.s   .aloop                  ; beyond load range
        movea.l d2,a3                   ; compare against orig
        move.w  d3,d6
        subq.w  #1,d6
.av:    move.b  (a1)+,d7
        cmp.b   (a3)+,d7
        bne.s   .trynew
        dbra    d6,.av
        bra.s   .aapply                 ; orig matched: write new
.trynew:movea.l d2,a3                   ; compare against new (already applied?)
        move.w  d3,d6
        subq.w  #1,d6
.an:    move.b  (a2)+,d7
        cmp.b   (a3)+,d7
        bne.s   .afail
        dbra    d6,.an
        bra.s   .aloop                  ; already applied
.aapply:movea.l d2,a3
        move.w  d3,d6
        subq.w  #1,d6
.aw:    move.b  (a2)+,(a3)+
        dbra    d6,.aw
        bra.s   .aloop
.afail: move.l  #'MWPF',MARKER.l
.adone: rts
