; name: pp_nofade
; default: yes
; image: HAGA
; edit: $0ffc 61000168
; edit: $16d8 6100fa8c
; edit: $1460 43fa004622b8007045fafe3821ca007046fc2300323a003643fa003e30015240eb48d2c0
; edit: $149c 46fc270021fa000600704e75
; note: removes PP's grey "loading" palette fade from his resident loader service
; note: (file HAGA, not RUNME.TOS; see work/notes/load_fade.md for the evidence).
; note: Offsets are HAGA file offsets (HB = RAM base of HAGA: $1F8000 on 2 MB, $F8000 on
; note: 1 MB). All listed addresses below are HB+offset, as in ram_ingame_lobos.bin.
; note:
; note: Original structure (all pc-relative, shared by 1 MB / 2 MB):
; note:   HB+$0fc4 service entry (every Fopen/Fseek/Fread/Fwrite/Fclose of the game)
; note:     bsr HB+$17be (save+stop MFP), bsr HB+$1166 (fade to grey + swap-in), trap #1 ...
; note:     bsr HB+$1372 (swap-out + fade back from grey)
; note:   HB+$16ac Fsfirst/Fsnext service: same bracket ($16d8 / $173e)
; note:   HB+$1b74 / $1f16 / $1f1e: the savestate/exit-to-desktop path, same two routines
; note:     (it needs its own grey fade: it draws text over the live screen)
; note: HB+$1166 saves $8240/$825e into HB+$1f86 and sets the flag byte HB+$1f8a (st.b),
; note:   fades every palette entry to a grey, one step per 2 VBL (stop #$2300 twice), at most 7 steps,
; note:   storing the palette before each step in HB+$14b8, the step count in HB+$14ac, then
; note:   (HB+$126e..) restores $70 and swaps in the TOS low memory (HB+$1278..$136e).
; note: HB+$1372 swaps the game low memory back and runs the fade-back loop HB+$1460..$14a6,
; note:   2 VBL per step down the saved palettes to the original one.
; note:
; note: Change: (1)+(2) the two service call sites call HB+$1278 (the swap-in tail, SR is
; note:   already $2700 there) instead of HB+$1166: no fade, no save of $8240/$825e, no st.b
; note:   of the flag HB+$1f8a. So HB+$1f8a is non-zero only inside the savestate path (its
; note:   entry calls HB+$1166 and its exit clears it).
; note: (3)+(4) the fade-back routine (HB+$1460) returns at once, SR and $70 untouched, when
; note:   HB+$1f8a is zero; otherwise it does exactly what it did (the saved $70 now lives on the
; note:   stack instead of HB+$14a8, and the a1 index uses lea d8(pc,d0.w) to save 4 bytes).
; note: The flag byte is zero in the shipped file and no other code touches it (grep of the
; note:   whole disassembly: only $1166, $1bd0 (tst), $1f22 (clr)).
        org     HB+$0ffc
        bsr.w   HB+$1278
        org     HB+$16d8
        bsr.w   HB+$1278
        org     HB+$1460
        move.b  HB+$1f8a(pc),d0
        beq.s   HB+$14a6
        move.l  $70.w,-(a7)
        lea     HB+$12a2(pc),a2
        move.l  a2,$70.w
        move.w  HB+$14ac(pc),d1
        move.w  d1,d0
        lsl.w   #5,d0
        lea     HB+$14d8(pc,d0.w),a1
        move    #$2300,sr
        nop
        org     HB+$149c
        move    #$2700,sr
        move.l  (a7)+,$70.w
        nop
        rts
