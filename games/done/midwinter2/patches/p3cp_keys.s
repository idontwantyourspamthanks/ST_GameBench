; name: p3cp_keys
; default: yes
; site: $315d0
; orig: 4eb84f664eb850ce
; note: Fire rate fix (work/notes/fire_rate.md).  The tail of the in-game frame loop, after the flip, is
;         $315d0  jsr $4f66.w   key fetch ($26e6c: $7684 -> $66d8/$66da, clears the latch)
;         $315d4  jsr $50ce.w   key / fire consumer ($1aaa4; J mode: `tst.w $6872 / clr.w $6872` at $1ab78, M/K mode: scancode $39 at $1ab86;
;                               a hand grenade, grenade launcher or flare has NO cooldown: one throw per call)
;         $315d8  jsr $30f72.l  F-key dispatcher (reads $66da)
;         $315de  bra.w $31486
;       The original runs the tail once per logic tick.  p3cp_head's extra passes (PH 2-5: `jmp $3158c` = HUD gauges, renderer, flip, then
;       the same tail) ran it too, so the key / fire consumers ran up to five times per 5 Hz tick (every 40 ms), and a J-mode fire that is held for one
;       tick re-armed `$6872` every VBL ($26b58, `move.w d2,$6872`) and threw a grenade in every pass: one press = 3 grenades.
;       The extra passes read no key and run no consumer any more: the tail jumps straight to the loop head (`$315de`).  PH 1 and plain passes
;       run the three calls as before (the blob is entered by `jmp`, so the stack depth at each `jsr` is the original's).
;       EXTRA = D+10 ($b42ea), set by p3cp_head's `.cont` path, cleared with SUB at every head entry; zero (stock behaviour) without p3cp_head.
EXTRA   equ     $b42ea
        org     $315d0
        jmp     $b7e00.l
        nop

        org     $b7e00
        tst.w   EXTRA.l
        bne.s   .skip
        jsr     $4f66.w                 ; displaced
        jsr     $50ce.w                 ; displaced
        jmp     $315d8.l                ; the F-key dispatcher and the loop branch follow
.skip:  jmp     $315de.l                ; extra pass: no key, fire or F-key processing
