; variant F (diagnostic): flip + rts only at the sync site; the $7b0a site only jumps back to $17c42
sync:   jsr     $d1ca.l
        rts
wait:   jmp     $17c42.l
vbl:    addq.b  #1,$611b.l
        rts
