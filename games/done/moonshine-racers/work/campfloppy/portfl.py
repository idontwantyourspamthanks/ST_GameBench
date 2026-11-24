#!/usr/bin/env python3
"""portfl.py: derive the FLOPPY port of MSRCampHD's cp_* patches from the CURRENT patches/cp_*.s (snapshot taken when this runs) into priv/patches/.
Changes (all in cp_title.s): the two HD sources (hard disk file / drive A through HAGA) become drive A / drive B read with the game's FDC driver; the HAGA reader is replaced
by the floppy reader (campread2.s: camp_read, rdsec, dpres) behind the same trk_read contract; an 'insert the disk' hint row.  The other six cp_* files only lose `; media: hd`."""
import re, sys
from pathlib import Path
H = Path(__file__).resolve().parent
P = H.parent.parent / "patches"; D = H / "priv" / "patches"
for f in sorted(P.glob("cp_*.s")):
    s = f.read_text()
    s = re.sub(r"^; media: hd\n", "", s, flags=re.M)
    if f.name == "cp_title.s":
        i = s.index("; ---- the HAGA-window file reader")
        s = s[:i]
        # sources
        s = s.replace('t_hd:   dc.b    "LOAD CAMPAIGN FROM HARD DISK",0', 't_hd:   dc.b    "LOAD CAMPAIGN FROM DRIVE A",0')
        s = s.replace('t_a:    dc.b    "LOAD CAMPAIGN FROM DRIVE A",0', 't_a:    dc.b    "LOAD CAMPAIGN FROM DRIVE B",0')
        s = s.replace('m_ldhd: dc.b    "LOADING CAMPAIGN FROM HARD DISK...",0', 'm_ldhd: dc.b    "LOADING CAMPAIGN FROM DRIVE A...",0')
        s = s.replace('m_lda:  dc.b    "LOADING CAMPAIGN FROM DRIVE A...",0', 'm_lda:  dc.b    "LOADING CAMPAIGN FROM DRIVE B...",0')
        s = s.replace('e_nf:   dc.b    "MSTRACKS.TRK NOT FOUND IN FILES",0', 'e_nf:   dc.b    "NO CAMPAIGN DISK IN DRIVE A",0')
        s = s.replace('e_nfa:  dc.b    "NO CAMPAIGN DISK IN DRIVE A",0', 'e_nfa:  dc.b    "NO CAMPAIGN DISK IN DRIVE B",0')
        s = s.replace('p_hd:   dc.b    "MSTRACKS.TRK",0', 'p_hd:   dc.b    "A:",0')
        s = s.replace('p_a:    dc.b    "A:\\MSTRACKS.TRK",0', 'p_a:    dc.b    "B:",0')
        assert 'p_a:    dc.b    "B:",0' in s and 'e_nfa:  dc.b    "NO CAMPAIGN DISK IN DRIVE B",0' in s and '"LOAD CAMPAIGN FROM DRIVE B"' in s
        s = s.replace("        clr.w   M_SEL.l\n        lea     pal(pc),a0", "        clr.w   M_SEL.l\n        clr.w   FL_FAIL.l\n        lea     pal(pc),a0", 1)
        s = s.replace("V_ACT   equ     CPV ", "FL_FAIL equ     CPWORK+$2B0     ; w  floppy reader: unit+1 of the last attempt that found no disk\nV_ACT   equ     CPV ", 1)
        s = s.replace(".sok:   lea     t_origon(pc),a0         ; status line", ".sok:   lea     t_ins(pc),a0\n        moveq   #2,d0\n        moveq   #20,d1\n        bsr     putline\n        lea     t_origon(pc),a0         ; status line", 1)
        s = s.replace('t_hint: dc.b', 't_ins:  dc.b    "INSERT THE CAMPAIGN DISK, THEN CHOOSE",0\nt_hint: dc.b', 1)
        rd = (H / "campread2.s").read_text()
        a = rd.index("camp_read:\n"); b = rd.index("; ------", rd.index("dpres:"))
        reader = rd[a:b]
        reader = reader.replace("        cmpi.l  #'MSTK',(a0)\n        bne     .out\n        move.w  6(a0),d0\n        beq     .out\n        cmpi.w  #15,d0\n        bhi     .out\n        move.l  8(a0),d0\n        cmp.l   v_size(a5),d0\n        bne     .out\n", "")
        reader = reader.replace("        movea.l v_dest(a5),a0\n        moveq   #6,d7\n", "")
        vars_ = """vars:   dc.w    0               ; v_unit
        dc.w    9               ; v_spt
        dc.w    2               ; v_spc
        dc.w    7               ; v_nroot
        dc.l    0               ; v_dest
        dc.l    0               ; v_max
        dc.l    0               ; v_size
        dc.l    0               ; v_root
        dc.l    0               ; v_data0
v_unit equ 0
v_spt equ 2
v_spc equ 4
v_nroot equ 6
v_dest equ 8
v_max equ 12
v_size equ 16
v_root equ 20
v_data0 equ 24
"""
        s += """
; ---- the floppy reader (work/campfloppy/campread2.s; notes work/notes/campaign_floppy.md): the game's own FDC driver sub_00cac0, FAT12 root directory, MSTRACKS.TRK contiguous
;   trk_read: a0 = "A:" / "B:" (the drive letter picks the unit), a1 = destination, d1 = maximum bytes
;   -> d0 = 0 ok | -33 no usable disk / not a FAT floppy / no MSTRACKS.TRK | 1 read error | $cd too big; d1 = bytes.  Same contract as the HAGA reader it replaces.
trk_read:
        movem.l d2-d4/a2,-(a7)
        moveq   #0,d0
        cmpi.b  #'B',(a0)
        bne.s   .u
        moveq   #1,d0
.u:     move.w  d0,d3                   ; unit
        lea     FL_FAIL.l,a2
        move.w  (a2),d2
        subq.w  #1,d2
        cmp.w   d0,d2
        seq     d2
        andi.w  #$ff,d2                 ; the previous attempt on THIS drive found no disk: do not probe, let the driver try
        movea.l a1,a0
        bsr.s   camp_read               ; d0.w status 0..5, d1.l size
        clr.w   (a2)
        moveq   #0,d4
        tst.w   d0
        beq.s   .x
        moveq   #1,d4                   ; 2 read error
        cmpi.w  #2,d0
        beq.s   .x
        move.l  #$cd,d4                 ; 5 too big
        cmpi.w  #5,d0
        beq.s   .x
        moveq   #-33,d4                 ; 1 no disk (probe), 3 not a FAT floppy, 4 no MSTRACKS.TRK
        cmpi.w  #1,d0
        bne.s   .x
        addq.w  #1,d3
        move.w  d3,(a2)
.x:     move.l  d4,d0
        movem.l (a7)+,d2-d4/a2
        rts

""" + vars_ + "\n" + reader.replace("        lea     vars(pc),a5\n        move.w  d0,v_unit(a5)", "        lea     vars(pc),a5\n        move.w  d0,v_unit(a5)") + "\nfname:  dc.b    \"MSTRACKSTRK\"\n        even\n"
    (D / f.name).write_text(s)
    print("wrote", D / f.name, len(s))
