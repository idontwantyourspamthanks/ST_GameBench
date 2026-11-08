; name: pp_bigram_cache
; default: yes
; image: HAGA
; edit: $3228 2412
; note: keeps PP's chunked disk cache on 68000 machines (ST, STE, Mega STE) with >= 4 MB RAM, so the
; note: payload at $B3000 survives.  Same HAGA file as Midwinter 2 (md5 b34607ed...), hence the same bytes.
; note: MW2 evidence (the hang at the "Flames of Freedom" title): games/midwinter2/work/notes/bigram.md.
; note: MW1: the images are $64000 bytes, so the whole-image cache would be $81000-$E5000 (work/notes/loading.md
; note: section 5, 4 MB boot of the original game), again over the payload.
; note:
; note: Bug (MW2 wording). PP's HAGA init routine (entry 13, HAGA+$3122, called once by RUNME) fills the 10-byte
; note:   cache record at HAGA+$3274 {buf.l = $81000, chunk.l = $30D40, flag.b}, which RUNME copies
; note:   into the low-RAM stub's cache descriptor ($3C4/$3C8/$3CC). With RAM code d1 >= 8
; note:   (HAGA+$87 = ST-RAM / 512 KB, i.e. >= 4 MB) the routine switches to "whole image" mode:
; note:   chunk := $B4000 (the 737280-byte FFA/FFB/FFC image), flag := $ff, and buf := max($81000,
; note:   a1) on a 68000, or $300100 when a 68020+ is present (HAGA+$88 != 0, TT/Falcon). The $200
; note:   stub then Freads the WHOLE image to $81000..$135000 on every cache miss, which zeroes
; note:   our payload at $B3000-$B4EFF (and then the game returns into zeros: hang).
; note:   Below 4 MB the record keeps its defaults: 200000-byte chunks, $81000..$B1D40.
; note:
; note: Original code (HAGA offsets):
; note:   $321c cmp.b #8,d1 ; $3220 bcs.b $3254          RAM < 4 MB: keep default record
; note:   $3222 move.b $88(pc),d2 ; $3226 bne.b $3232    68020+: buf := $300100
; note:   $3228 move.l (a2),d2 ; cmpa.l d2,a1 ; ble ; move.l a1,(a2)   68000: buf := max($81000,a1)
; note:   $3232 move.l #$300100,(a2)
; note:   $3238 move.l a0,4(a2) (chunk := image size) ; st.b 8(a2) (flag) ; ... ; $326e rts
; note:   $3254 d2 := HAGA+$83 (machine type, 5 = TT) -> TT-only record, else falls to $326e
; note:
; note: Change: the 68000 branch of the whole-image block (first instruction at $3228,
; note:   `move.l (a2),d2`) becomes `bra.b $3254`, i.e. 68000 machines take the same path as
; note:   RAM < 4 MB (default record, chunked reads at $81000..$B1D40, as on 1 MB/2 MB).
; note:   68020+ machines (buf $300100, clear of $B3000) keep PP's whole-image mode unchanged.
; note:   The following 14 bytes ($322a-$3237) become unreachable; no other bytes change.
        org     HB+$3228
        bra.b   HB+$3254
