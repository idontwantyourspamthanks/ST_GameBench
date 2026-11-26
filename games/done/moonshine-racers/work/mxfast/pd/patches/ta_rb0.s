; name: ta_rb0
; default: no
; site: $d57c
; orig: 303812fe323813005b4111c0fa21
; requires: ta_rb
; doc: Raster list, part 2: when ta_rb's cache holds the compact list for the current ($12fe,$1300) and sky colours, the stock list builder is skipped altogether (saves its ~350 cycles per VBL).
; note: Tighten wave A.  Site $d57c: the first four instructions of the VBL's raster-list builder (`move.w $12fe.w,d0 / move.w $1300.w,d1 / subq.w #5,d1 / move.b d0,$fa21.w`, 14 bytes) -> `jmp $BED00.l` + nops.
; note: Hit (same KEY long $12fe/$1300 and the same 9 colour words $3cc4-$3cd5 as when ta_rb built the cached list): the blob writes $fa21, points $3cbc at the cached colour table, copies the cached compact list to $3d0e, does the `bset.b #0,$fa07.w` that follows the stock builder and jumps to $d5ec (the stock code after it).
; note: Miss: the displaced four instructions, then `jmp $d58a.l`: the stock builder runs and ta_rb's hook at $d5e6 compacts the list and fills the cache.  Cache data: ta_rb's $BEE00.
KEY     equ     $BEE00
KCOL    equ     $BEE04
FIRST   equ     $BEE16
NL      equ     $BEE18
LST     equ     $BEE20
CT      equ     $BEE50
        org     $d57c
        jmp     $BED00.l

        org     $BED00
rb0:    move.l  $12fe.w,d0
        cmp.l   KEY.l,d0
        bne.s   .miss
        lea     $3cc4.w,a0
        lea     KCOL.l,a1
        cmpm.l  (a0)+,(a1)+
        bne.s   .miss
        cmpm.l  (a0)+,(a1)+
        bne.s   .miss
        cmpm.l  (a0)+,(a1)+
        bne.s   .miss
        cmpm.l  (a0)+,(a1)+
        bne.s   .miss
        cmpm.w  (a0)+,(a1)+
        bne.s   .miss
        move.b  FIRST+1.l,$fffffa21.w
        move.l  #CT,$3cbc.l
        lea     LST.l,a0
        lea     $3d0e.w,a1
        move.w  NL.l,d0
.cp:    move.l  (a0)+,(a1)+
        dbra    d0,.cp
        bset.b  #0,$fffffa07.w
        jmp     $d5ec.l
.miss:  lea     $3d0e.w,a0              ; the stock builder expects the list pointer in a0 (the compare above used it)
        move.w  $12fe.w,d0
        move.w  $1300.w,d1
        subq.w  #5,d1
        move.b  d0,$fffffa21.w
        jmp     $d58a.l
