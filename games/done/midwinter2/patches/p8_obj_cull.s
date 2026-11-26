; name: p8_obj_cull
; default: yes
; site: $1c4b2
; orig: 30386fc8b07cff806d00ff6a
; phase: deferred
; note: Static scenery object distance culling in MEDIUM & LOW detail (sub_01c3fc -> $1c436 path ONLY;
; note: vehicles/enemies at $1c508 and effects/explosions at $1c656 are NEVER culled).
; note: In HIGH detail (LEVEL=0), executes only the original Z check (100% pixel-identical).
; note: In MEDIUM/LOW, skips static scenery objects with max(|obj.x - player.x|, |obj.y - player.y|) > OBJ_LIM ($B910A).
DET     equ     $b9100
oLVL    equ     0
oOBJLIM equ     10

        org     $1c4b2
        jmp     $b9960.l
        nop
        nop
        nop

        org     $b9960
        move.w  $6fc8.w,d0              ; displaced
        cmp.w   #$ff80,d0               ; displaced
        blt.s   .skip
        tst.w   DET+oLVL.l
        beq.s   .draw
        move.l  $53e4.w,d1
        sub.l   $66e6.w,d1
        bpl.s   .dxp
        neg.l   d1
.dxp:   cmp.l   DET+oOBJLIM.l,d1
        bgt.s   .skip
        move.l  $53e8.w,d1
        sub.l   $66ea.w,d1
        bpl.s   .dyp
        neg.l   d1
.dyp:   cmp.l   DET+oOBJLIM.l,d1
        bgt.s   .skip
.draw:  jmp     $1c4be.l
.skip:  jmp     $1c426.l
