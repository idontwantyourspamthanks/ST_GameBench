; name: pp_bigram_cache
; default: yes
; image: HAGA
; edit: $3228 2412
; doc: PP's loader keeps its chunked disk cache at 4 MB or more on ST/STE/Mega ST/STE (no whole-image reads over the patch area).
; note: Keeps PP's HAGA disk cache in chunk mode on 68000 machines (ST, STE, Mega ST/STE) with >= 4 MB RAM, as it is below 4 MB.  Same edit as Midwinter 2
; note: (HAGA is byte-identical: md5 b34607ed...).  Without it HAGA's init (HAGA+$3122) switches to "whole image" mode at RAM code >= 8 (4 MB):
; note: RUNME then Freads the whole MS1 (286,507 B) / MS2 (772,096 B) to $81000.. on every cache miss, which overwrites everything up to
; note: $C6F2B / $13D7FF, including the patch payload at $B2700.  The pristine game works at 4 MB; only added code breaks (work/notes/delivery.md).
; note: Change: the 68000 branch of the whole-image block (`move.l (a2),d2` at HAGA+$3228) becomes `bra.b $3254`: the default record, chunked reads
; note: of 200,000 B at $81000-$B1D40.  68020+ (TT/Falcon) keep PP's whole-image mode (cache at $300100, clear of the payload).
        org     HB+$3228
        bra.b   HB+$3254
