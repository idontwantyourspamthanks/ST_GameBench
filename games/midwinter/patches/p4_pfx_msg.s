; name: p4_pfx_msg
; default: no
; site: $14ed6
; note: item #5 part 4/4. sub_014e98 draws the "ENEMY IN RANGE" message (x=$a0,y=$64 = inside the 3D window rows) with
; note: $117d8 AFTER the goggles replay of the same frame, into the draw buffer. Those pixels are not part of the
; note: sky+goggles image, so forget all clean prefixes whenever the message is drawn (it is redrawn every frame while
; note: its timer $14ee4 >= 0). Displaces `lea.l $14ee6.l,a1`.
KB      equ     $b4800
CK      equ     $b4808
        org     $14ed6
        jmp     $b44e0.l
        org     $b44e0
        lea     $14ee6.l,a1             ; displaced
        clr.l   KB.l
        clr.w   KB+4.l
        clr.w   CK.l
        jmp     $14edc.l
