; name: test_blob36k
; default: no
; site: $6f5e
; orig: 41f900070000
; conflicts: test_marker mr_edge                  ; same site $6f5e; its ramp $B3100-$B311F lies inside mr_edge's blob $B3040-$B3289
; data: $C16FF 1 free
; data: $B3100 32
; note: Payload-capacity test, same site as test_marker: the image is padded to the `IMG_MAX_LEN` limit ($B2700-$C16FF, 61,440 B) by a blob at $B3000
; note: (beyond the image's natural end, so the whole image must be copied) and 1 byte of `free` data at $C16FF, the last image byte (not copied, must survive).
; note: The blob (code $B3000-$B3025) writes 'MSTM' at $B2FF0 and a 16-word ramp at $B3100, then jumps back to $6f64.  A pass proves that the bigger RUNME data segment loads and sizes
; note: correctly on 1 MB and that the copy routine's D0 count covers the whole image.  Results in work/notes/delivery.md section 4.
        org     $6f5e
        jmp     $B3000.l

        org     $B3000
        move.l  #'MSTM',$B2FF0.l
        lea     $B3100.l,a1
        moveq   #15,d0
        move.w  d0,d1
.f:     move.w  d1,(a1)+
        subq.w  #1,d1
        dbra    d0,.f
        lea     $70000.l,a0
        jmp     $6f64.l
