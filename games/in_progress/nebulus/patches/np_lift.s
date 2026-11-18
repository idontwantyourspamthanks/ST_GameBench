; Nebulus performance patch np_lift (NebLiftPerf): cheaper empty-cell test in the tower-surface cell scans.  In-place, same size, no RAM blob.
; The tower renderer sub_037b1c walks 16 columns x ~22 cells per frame twice (sub_037c06: door pass, sub_037cd6: tile pass).  For every cell it did
;     clr.w d0 / move.b -(a3),d0 / move.b (a5,d0.w),d0 / cmp.b #$28,d0 / bcc.w skip         (46 cycles, then 18 for adda+dbra)
; with a5 = the class table $315e0 (built once by sub_038028: every byte value with bit 7 clear -> class $f6, i.e. "skip"; with bit 7 set -> $00 $0a $14 $1e $28).
; Cells with bit 7 clear (empty space, enemy markers, lift end/stop markers: the large majority) are therefore always skipped, so the move.b that
; loads the cell sets N and `bpl.b skip` leaves right after it (24 cycles).  Cells with bit 7 set take the unchanged class-table path.
; The branch to `skip` is the same target as before; d0 differs only on the skipped path where it is dead (reloaded by clr.w d0 at the next cell / loop exit).
; ---- site 37d5a   (sub_037cd6 inner loop, 8 cells per column, 16 B, orig: clr.w d0 / move.b -(a3),d0 / move.b (a5,d0.w),d0 / cmp.b #$28,d0 / bcc.w $37d8a)
        org $37d5a
        clr.w d0
        move.b -(a3),d0
        bpl.b $37d8a
        move.b (a5,d0.w),d0
        cmp.b #$28,d0
        bcc.b $37d8a
; ---- site 37d0c   (sub_037cd6 first cell of a column, 16 B, orig ... bcc.w $37d46)
        org $37d0c
        clr.w d0
        move.b -(a3),d0
        bpl.b $37d46
        move.b (a5,d0.w),d0
        cmp.b #$28,d0
        bcc.b $37d46
; ---- site 37d90   (sub_037cd6 last cell of a column, 16 B, orig ... bcc.w $37dba)
        org $37d90
        clr.w d0
        move.b -(a3),d0
        bpl.b $37dba
        move.b (a5,d0.w),d0
        cmp.b #$28,d0
        bcc.b $37dba
; ---- site 37c74   (sub_037c06 inner loop, 14 B, orig: clr.w d0 / move.b -(a3),d0 / cmpi.b #$28,(a5,d0.w) / bne.w $37c8e)
        org $37c74
        clr.w d0
        move.b -(a3),d0
        bpl.b $37c8e
        cmpi.b #$28,(a5,d0.w)
        bne.b $37c8e
; ---- site 37c42   (sub_037c06 first cell, 14 B, orig ... bne.w $37c68)
        org $37c42
        clr.w d0
        move.b -(a3),d0
        bpl.b $37c68
        cmpi.b #$28,(a5,d0.w)
        bne.b $37c68
; ---- site 37c96   (sub_037c06 last cell, 14 B, orig ... bne.w $37cb2)
        org $37c96
        clr.w d0
        move.b -(a3),d0
        bpl.b $37cb2
        cmpi.b #$28,(a5,d0.w)
        bne.b $37cb2
