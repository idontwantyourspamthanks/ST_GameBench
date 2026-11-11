; name: p4_proj_div
; default: yes
; site: $200ce
; orig: 3e3866e081c783c7
; note: $200b4 marker pass. d0=long/$66e0, d1=long/$66e0 via 2 divs.w (~150 cy each).
;       $66e0 has no absolute-short writer (xref: 6 readers, 0 writers), so it is
;       guarded at runtime: if $66e0 == 512 and x*128 does not overflow (V clear, i.e.
;       x in [-2^24,2^24-1], so the quotient fits a word; otherwise divs would overflow
;       and leave d0/d1 unchanged) use a sign-correct truncating shift: t=x<<7, if t<0
;       t+=511<<7, swap => (x<0 ? x+511 : x)>>9. Otherwise the original divs run, with
;       the dividends reloaded from the record.
;       d7=$66e0 kept. Upper words of d0/d1 (divs remainder) are dead: next uses are
;       move.w/sub.w/neg.w/cmp.w and muls.w, which overwrite both whole registers.
;       No other register is touched.
        org     $200ce
        jsr     $b3880.l
        nop

        org     $b3880
        move.w  $66e0.w,d7
        cmp.w   #512,d7
        bne.s   slow
        asl.l   #7,d0                   ; x*128; V = x outside [-2^24,2^24-1]
        bvs.s   slow                    ;  -> quotient may not fit a word: let divs decide
        bpl.s   pa
        add.l   #65408,d0               ; +511*128: truncate toward zero like divs
pa:     swap    d0                      ; low word = (x [+511]) >> 9
        asl.l   #7,d1
        bvs.s   slow
        bpl.s   pb
        add.l   #65408,d1
pb:     swap    d1
        rts
slow:   move.l  $12(a0),d0              ; original dividends (fast path clobbered them)
        move.l  $16(a0),d1
        divs.w  d7,d0
        divs.w  d7,d1
        rts
