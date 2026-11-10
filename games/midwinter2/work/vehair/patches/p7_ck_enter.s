; name: p7_ck_enter
; default: yes
; site: $1fa54
; orig: 49f90007c718
; phase: deferred
; note: P7 items 1+2, part 2/5 (work/notes/p7_cockpit_cull.md).  Terrain pass entry $1fa54 (the only
;       caller is `bsr.w $1fa54` at $1dcaa inside $1dc12).  Sets EN ($b5000) = 1 when the cockpit
;       replay is guaranteed to follow this pass and to cover the pixels the table calls opaque:
;         - called from the main renderer: 4(a7) = $1dbe2 (return address of `jsr $505c` at $1dbde;
;           the alternate scene render $327e6 enters $505c from $328e2 and never replays the
;           cockpit, same discrimination as p4_hud_pfx_fill),
;         - the replay runs: $6220 not in {5, $15, $11} (the three compares at $1dbee-$1dc04),
;       and builds the table first if it is still empty (BUILT = 0: live-applied snapshots, or a boot
;       before the first 3D-view entry).  EN is cleared again at the end of the pass (p7_ck_exit), so
;       that polygon fills outside a terrain pass never see it.
;       Displaces `lea.l $7c718.l,a4`; d0 is dead at entry ($1fa54 first writes d0 at $1fa8e).
EN      equ     $b5000
BUILT   equ     $b5002
BUILDSAFE equ   $b5290

        org     $1fa54
        jmp     $b5494.l

        org     $b5494
        lea     $7c718.l,a4             ; displaced
        clr.w   EN.l
        cmpi.l  #$1dbe2,4(a7)
        bne.s   .x
        move.w  $6220.w,d0
        cmp.w   #5,d0
        beq.s   .x
        cmp.w   #$15,d0
        beq.s   .x
        cmp.w   #$11,d0
        beq.s   .x
        tst.w   BUILT.l
        bne.s   .on
        jsr     BUILDSAFE.l
.on:    move.w  #1,EN.l
.x:     jmp     $1fa5a.l
