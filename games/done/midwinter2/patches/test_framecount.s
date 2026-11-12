; name: test_framecount
; default: no
; site: $3159c
; orig: 427870204eb85086
; data: $b34f0 4
; note: per-frame counter. Replaces `clr.w $7020.w; jsr $5086.w` in the frame
;       loop (work/notes/frameloop.md #30/#31) with a jsr into the blob at
;       $b3480, which bumps the blob-owned long at $b34f0 and then performs
;       the displaced instructions exactly.
        org     $3159c
        jsr     $b3480.l
        nop                             ; pads the 8-byte site

        org     $b3480
        addq.l  #1,$b34f0.l             ; blob-owned frame counter
        clr.w   $7020.w                 ; displaced instruction
        jsr     $5086.w                 ; displaced instruction (-> $20272)
        rts
