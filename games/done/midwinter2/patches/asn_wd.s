; name: asn_wd
; default: yes
; site: $262c2
; orig: 4eb900027228
; phase: boot
; note: (code: patches/asn/blob.s)  Watchdog of asn_core and asn_mus (work/notes/amiga_sound.md): the VBL handler `$26298` calls `jsr $27228.l` at `$262c2`; it becomes `jsr asn_wd.l` (6 B).
; note: The blob's ticks (sound effects in the 3D view, music elsewhere; heartbeat SV+12) run only while the game's tick pointer `$5138` is theirs.
; note: If the previous VBL's tick did not run, the session is over: the DMA is stopped (a looped ring would repeat its last 164 ms for ever) and
; note: the next session starts clean.  Then `jmp $27228.l` replays the displaced call (its rts returns to the handler).
        org     $262c2
        jsr     $bf806.l
