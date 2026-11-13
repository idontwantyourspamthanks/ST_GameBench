; name: sav_sync
; default: no
; hdonly: yes
; requires: sav_hook
; site: $c02d4
; orig: 46fc27004238fa07
; note: Durability of a save (part of sav_hook's feature, work/notes/save.md section 4).  PP's loader Fcloses every file
; note: (`$c02ca move.w d7,-(a7) / move.w #$3e,-(a7) / trap #1 / addq.l #4,a7`), and the file DATA is written at once - but the
; note: directory entry and the FAT chain live in GEMDOS's disk buffers, which GEMDOS writes back only when the buffer has to be
; note: reused (EmuTOS bdos/fsbuf.c: `flush()` is called from `getbuf()` on eviction).  A machine switched off after a save could
; note: therefore lose the slot's directory entry: measured, killing Hatari 1 s and 20 s after the save lost SAVES.DIR in 3 of 3 and
; note: 2 of 3 runs.  Here, after a WRITE (`$c0742` is still $5772 here; the loader clears it at $c034e), GEMDOS's `Dfree` is called:
; note: it reads the whole FAT (EmuTOS bdos/fsfat.c `xgetfree` -> `countfree16` -> `getrec` per FAT record), which evicts every dirty
; note: buffer, so the directory and FAT sectors reach the disk at once.  Dfree = GEMDOS function $36 with both arguments on the
; note: stack, exactly as the Compendium documents it: `move.w drive,-(a7) / pea buf / move.w #$36,-(a7) / trap #1 / addq.l #8,a7`
; note: (drive 0 = current; buf = a 16-byte result area).  It runs inside the loader's
; note: TOS window (the vector table is swapped back only at $c02f8), costs one FAT scan per save and nothing on a read.
SAVSYNC equ     $8cb80

        org     $c02d4
        jmp     SAVSYNC.l
        nop                             ; never executed: the blob returns to $c02dc (both replaced instructions re-run)
                                        ; the 8 bytes `move.w #$2700,sr / clr.b $fa07` are re-run by the blob

        org     $8cb80
sav_sync:
        cmpi.w  #$5772,$c0742.l         ; write mode?  (a read leaves the buffers as GEMDOS had them)
        bne.s   .plain
        movem.l d0/a0-a1,-(a7)
        clr.w   -(a7)                   ; drive 0 = the current one (\FILES lives there)
        pea     buf(pc)                 ; Dfree(buf, drive): drive word, then the pointer, then the function
        move.w  #$36,-(sp)
        trap    #1
        addq.l  #8,a7
        movem.l (a7)+,d0/a0-a1
.plain: move.w  #$2700,sr               ; the replaced instructions
        clr.b   $fffffa07.w
        jmp     $c02dc.l
        even
buf:    ds.l    4
