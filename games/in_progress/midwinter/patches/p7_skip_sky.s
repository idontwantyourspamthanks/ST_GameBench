; name: p7_skip_sky
; default: yes
; site: $14e20
; orig: 4eb90001580e
; note: P7 static-frame skip (work/notes/p7_static_skip.md), part 1/2: the sky fill call of the frame (`jsr $1580e` at $14e20) is
; note: deferred.  The skip decision can only be taken at the marker call `jsr $1d0a0` ($14e50, p7_skip_render), i.e. after the
; note: object logic ($202c6..$20d52) has run, so the sky fill, which writes the window of the draw buffer, must not run before it.
; note: The blob either runs the original sky fill at once (jmp $1580e: the stack and the return $14e26 are exactly those of the
; note: original call, which p4_pfx_fill checks via 64(a7)) while p7_skip_render has never run (ENABLE = 0: the patch set without
; note: p7_skip_render keeps the original behaviour), or only sets PEND = 1 and returns; p7_skip_render's hook then runs the sky
; note: fill itself (same stack layout) when it renders, or drops it when it skips.  Needs p7_skip_render for the deferral.
ENABLE  equ     $b6000
PEND    equ     $b6002
        org     $14e20
        jsr     $b5800.l

        org     $b5800
        tst.w   ENABLE.l
        bne.s   .defer
        jmp     $1580e.l
.defer: move.w  #1,PEND.l
        rts
