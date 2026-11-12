; name: p4_proj_cols
; default: yes
; site: $3c02a
; orig: 301032280006
; note: $3c02a (scalar x column-sum pairs). The loop body computed s*d3+s*d4+s*d5 (and
;       s*d0+s*d1+s*d2) with 6 muls although d0-d5 are loop invariant. Since
;       s*a+s*b+s*c == s*(a+b+c) (mod 2^32) the sums are hoisted: 2 muls per scalar.
;       Valid only if each column sum fits a signed word (muls takes the low word):
;       checked per call (3/object); otherwise jumps back into the original code at
;       $3c034 (d3-d5 reloaded there, d0-d2 untouched until the check passes).
;       Exit contract kept: a0,a1,a2(advanced),a3(advanced),d7=$ffff; d0-d6,a5 are
;       dead for all 3 callers ($3be92/$3bea0/$3beae -> next use reloads or $3c080
;       reloads a0-a3,a5,d6,d7 and d0-d5 before reading them).
        org     $3c02a
        jmp     $b3800.l

        org     $b3800
        move.w  (a0),d0                 ; displaced
        move.w  6(a0),d1                ; displaced
        move.w  $c(a0),d2
        move.w  (a1),d3
        move.w  6(a1),d4
        move.w  $c(a1),d5
        movea.w d3,a5                   ; sum of a1 column (long)
        adda.w  d4,a5
        adda.w  d5,a5
        move.w  a5,d6
        ext.l   d6
        cmpa.l  d6,a5                   ; fits a word?
        bne.s   fb
        move.w  a5,d3                   ; d3 = sum1 (d4,d5 free; fb reloads them)
        movea.w d0,a5                   ; sum of a0 column
        adda.w  d1,a5
        adda.w  d2,a5
        move.w  a5,d6
        ext.l   d6
        cmpa.l  d6,a5
        bne.s   fb
        move.w  a5,d0                   ; d0 = sum0
        bra.s   dbr
loop:   move.w  (a2)+,d6
        move.w  d6,d5
        muls.w  d3,d6
        asl.l   #2,d6
        swap    d6
        move.w  d6,(a3)+
        muls.w  d0,d5
        asl.l   #2,d5
        swap    d5
        move.w  d5,(a3)+
dbr:    dbra    d7,loop
        rts
fb:     jmp     $3c034.l                ; original body: reloads d3-d5, d0-d2 intact
