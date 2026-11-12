; name: p4_clamp
; default: yes
; stage: 2
; site: $1942
; orig: 13f90001c4910001c48f
; note: PMBusErr, work/notes/buserr.md: safety net for the IKBD packet parser.  The game polls the IKBD every VBL (`$0D`, absolute mouse
;       positions, set up at start-up with `$09 $013f $00c7` = x 0..319, y 0..199) and the 6-byte reply is parsed byte by byte by the ACIA
;       handler `$18be` (state `$1c48e`: `$f7` header -> 5 data bytes into `$1c491..$1c495`).  A lost byte (ACIA overrun: an interrupt kept
;       waiting longer than one 1.28 ms byte) shifts the packet: the next header or the joystick packet is eaten as data, and the position
;       words become garbage (observed: x = $0000, y = $adfd); `$13c4` then draws the pointer at `$2df78 + y*160`, a bus error.  The parser
;       resynchronises by itself at the next header (the next VBL), but the draw of that one VBL is fatal.
;       `$1942` is the packet-complete branch (`move.b $1c491.l,$1c48f.l`, the button byte, 10 bytes; the two position copies `$194c`
;       and `$1956` follow).  This hook runs the displaced instruction, then checks the shadow position `$1c492` (x) and `$1c494` (y):
;       if x > 319 or y > 199 (unsigned) the packet is dropped, i.e. the shadow words are set back to the last committed position
;       `$2df92` / `$2df94` and the copies that follow are no-ops.  Every position the IKBD can really send is in range, so nothing
;       changes in normal use.  (test_walk2/3, the pmab pointer driver, replace the copies at `$194c` / `$1956`: independent of this hook.)
        org     $1942
        jsr     $bd400.l
        nop
        nop

        org     $bd400
clamp:  move.b  $1c491.l,$1c48f.l       ; the displaced instruction
        cmpi.w  #319,$1c492.l
        bhi.s   .bad
        cmpi.w  #199,$1c494.l
        bls.s   .ok
.bad:   move.w  $2df92.l,$1c492.l       ; keep the last good position
        move.w  $2df94.l,$1c494.l
.ok:    rts
