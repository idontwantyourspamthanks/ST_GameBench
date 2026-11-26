; name: fl_hook
; default: yes
; media: floppy
; disk: A $c350 21fc00006f5a00884e42
; note: The floppy build's hook: the game's own entry stub `move.l #$6f5a,$88.w` + `trap #2` is patched on disk A ($C350 = RAM $6f50)
; note: to `jmp $B2708.l` + nops, so the trampoline (patches/core_floppy.s) runs when the loader starts the game: every RAM patch site is
; note: loaded at that instant, the same all-or-nothing verify/apply as the HD build runs, and the trampoline ends by replaying the
; note: displaced two instructions.  The loader itself and the disk-swap behaviour are untouched.
        org     $c350
        jmp     $B2708.l
        nop
        nop
