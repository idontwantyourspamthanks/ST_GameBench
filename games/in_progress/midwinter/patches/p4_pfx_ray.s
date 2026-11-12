; name: p4_pfx_ray
; default: yes
; site: $1d710
; note: item #5 fix (part of the p4_pfx_* set; 5/5). sub_01d5a6's tail case (`$1d710 jsr $20e4e`, the only caller of
; note: $20e4e) runs the enemy-impact ray effect: $20e4e -> 64 x $20f00 -> $6ed8 draws rays with the line routine
; note: straight into the draw buffer ($12d0a) after the sky fill, over the window ($20e68-$20e80 set the clip to
; note: $171f0-$171f6), with no polygon, so YMIN never sees them. Unpatched, the next fill of that buffer wipes the rays;
; note: with the clean prefix the sky rows were skipped and the rays stayed ("ghost rays": 783 px in $78000,
; note: enemy snapshot, work/notes/p4_raster.md section 8). Fix: when the effect runs, set YMIN = 0 so the new KB[b]
; note: (and the replay's min(old,new)) becomes 0: this frame's replay is full and this buffer's next fill is full.
; note: Tail jump: $20e4e returns to $1d716 as before.
YMIN    equ     $b4806
        org     $1d710
        jsr     $b4700.l
        org     $b4700
        clr.w   YMIN.l
        jmp     $20e4e.l
