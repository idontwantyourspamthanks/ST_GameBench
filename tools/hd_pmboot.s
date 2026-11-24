; PMBOOT.PRG - AUTO-folder boot prompt for the Powermongers on the all-games hard disk (tools/make_hd_image.py wraps it into a .PRG).
;
; Why: the Powermonger HD builds must be started from the AUTO folder (games/done/powermonger/work/notes/loading.md section 7.1: they
; copy TOS's low RAM aside; started from the GEM desktop that region is too big and the game stops with "cannot swap the low
; RAM of TOS").  Powermonger: World War 1 Edition uses the same HD loader.  A bare AUTO\<game>.PRG would start a game on every
; boot; this program asks first:
;     "P Powermonger, W WW1, else desktop" (3 s, or any other key)
; P: current directory := \POWERMON (the game looks for DATA\, PMLATE.DAT and SAVEDISK.DAT in the folder it was started from),
;    Pexec(\POWERMON\WAR.PRG).
; W: current directory := \PMWW1 (WW1.PRG, its data files and SAVEDISK.DAT are in that folder), Pexec(\PMWW1\WW1.PRG).
; Other key / timeout / program missing: return, TOS goes on to the desktop.
; Position independent, no relocation.  Uses only GEMDOS (works from user or supervisor mode, i.e. in the AUTO phase).
WAIT_HZ equ 600                         ; 3 s at 200 Hz
STK     equ 400

start:  move.l  4(sp),a5                ; our basepage
        move.l  $c(a5),d0               ; text + data + bss
        add.l   $14(a5),d0
        add.l   $1c(a5),d0
        add.l   #$100,d0
        lea     stkend(pc),sp
        move.l  d0,-(sp)                ; Mshrink(0, bp, len): keep only ourselves, the child needs RAM
        move.l  a5,-(sp)
        clr.w   -(sp)
        move.w  #$4a,-(sp)
        trap    #1
        lea     12(sp),sp

        pea     msg(pc)
        move.w  #9,-(sp)                ; Cconws
        trap    #1
        addq.l  #6,sp

        pea     gethz(pc)
        move.w  #38,-(sp)               ; Supexec: d0 = _hz_200
        trap    #14
        addq.l  #6,sp
        move.l  d0,d6
        add.l   #WAIT_HZ,d6             ; deadline
wait:   move.w  #11,-(sp)               ; Cconis: key waiting (a key pressed earlier in the boot is in the buffer already)
        trap    #1
        addq.l  #2,sp
        tst.w   d0
        bne.s   key
        pea     gethz(pc)
        move.w  #38,-(sp)
        trap    #14
        addq.l  #6,sp
        sub.l   d6,d0
        bmi.s   wait                    ; now < deadline
        bra.s   done
key:    move.w  #8,-(sp)                ; Cnecin
        trap    #1
        addq.l  #2,sp
        and.b   #$df,d0                 ; upper case
        lea     pm_dir(pc),a3
        lea     pm_prog(pc),a4
        cmp.b   #'P',d0
        beq.s   run
        lea     ww_dir(pc),a3
        lea     ww_prog(pc),a4
        cmp.b   #'W',d0
        bne.s   done

run:    move.l  a3,-(sp)                ; Dsetpath(dir)
        move.w  #$3b,-(sp)
        trap    #1
        addq.l  #6,sp
        clr.l   -(sp)                   ; Pexec(0, prog, "", 0): never returns when the game runs
        pea     noargs(pc)
        move.l  a4,-(sp)
        clr.w   -(sp)
        move.w  #$4b,-(sp)
        trap    #1
        lea     16(sp),sp
        pea     nomsg(pc)               ; only reached when the program could not be started
        move.w  #9,-(sp)
        trap    #1
        addq.l  #6,sp
        move.l  a4,-(sp)
        move.w  #9,-(sp)
        trap    #1
        addq.l  #6,sp
done:   pea     crlf(pc)
        move.w  #9,-(sp)
        trap    #1
        addq.l  #6,sp
        clr.w   -(sp)                   ; Pterm0: on to the desktop
        trap    #1

gethz:  move.l  $4ba.w,d0
        rts

msg:    dc.b    13,10,"P Powermonger, W WW1, else desktop",0      ; <= 39 columns (low resolution)
nomsg:  dc.b    13,10,"not started: ",0
crlf:   dc.b    13,10,0
pm_dir: dc.b    "\POWERMON",0
pm_prog: dc.b   "\POWERMON\WAR.PRG",0
ww_dir: dc.b    "\PMWW1",0
ww_prog: dc.b   "\PMWW1\WW1.PRG",0
noargs: dc.b    0,0
        even
        ds.b    STK
stkend:
