; name: p4_div_b
; default: yes
; site: $1d164
; note: item #7 (render.md s8), site B. sub_01d14a object marker test (4 slots): `move.w $12c5a.l,d7 / divs.w d7,d0 / divs.w d7,d1`
; note: (d0=long $6(a0), d1=long $a(a0), 2 x ~150 cy). Ported from MW2 p4_proj_div. $12c5a is $0200 in the
; note: file (bytes 0200 0008 at $12c5a, disassembled as `andi.b #8,d0`) and has NO store in the whole resident
; note: code (grep of tools/m68dis.py output $800-$31698: 6 `move.w $12c5a.l,d7/d0/d2` readers only).
; note: Guarded at run time anyway: d7 == 512 and x*128 does not overflow (V clear <=> x in [-2^24,2^24-1], so
; note: the divs quotient fits a word); then truncating toward zero = (x<0 ? x+511 : x) >> 9 done as
; note: t=x<<7 (+511<<7 if t<0), swap. Otherwise the original divs run (dividends reloaded from the record).
; note: Upper words of d0/d1 (divs remainder) are dead: the next uses are move.w/sub.w/cmp.w/muls.w, all on
; note: the low word. d7 = $12c5a is kept. 10 site bytes: jmp (6) + 4 bytes of dead filler; the blob ends in jmp $1d16e.
        org     $1d164
        jmp     $b3c60.l
        nop
        nop

        org     $b3c60
        move.w  $12c5a.l,d7
        cmp.w   #512,d7
        bne.s   .slow
        asl.l   #7,d0                   ; V = x outside [-2^24,2^24-1]
        bvs.s   .slow
        bpl.s   .pa
        add.l   #65408,d0               ; +511*128: truncate toward zero like divs
.pa:    swap    d0
        asl.l   #7,d1
        bvs.s   .slow
        bpl.s   .pb
        add.l   #65408,d1
.pb:    swap    d1
        jmp     $1d16e.l
.slow:  move.l  $6(a0),d0               ; original dividends (the fast path clobbered them)
        move.l  $a(a0),d1
        divs.w  d7,d0
        divs.w  d7,d1
        jmp     $1d16e.l
