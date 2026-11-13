; name: sky_vblx
; default: no
; site: $c61c
; orig: 08ad0007008f
; requires: sky_vbl
; note: The Amiga's sky, part 7 of 7: the end of the VBL handler (`bclr #7,$8f(a5)`, 6 B, just before `movem.l (a7)+ / rte`).
; note: On a frame with the sky armed, sky_vbl lets the rest of the handler run at IPL 5 with the IKBD masked in the MFP, so
; note: that only Timer B can interrupt it (a band in the top rows is then on time even when the handler, with the DMA mixer,
; note: runs into the picture).  This exit puts IPL 7 and the IKBD mask back.  The code is in sky_vbl.s; work/notes/visuals.md.
SKY     equ     $8f100

        org     $c61c
        jmp     SKY+24.l                ; sky_vblx: returns to $c622
