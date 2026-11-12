; name: p4_testfar
; default: no
; data: $bd000 1024
; note: gate for the sparse payload (work/notes/loading.md section 3): blobs at the far ends of the p4_ range and a data
;       reservation, so the flat image spans $B8000..$BD3FF but only the records cost disk bytes.  Never applied.
        org     $bd400
        dc.b    'PMFAR1'
        org     $cd000
        dc.b    'PMFAR2'
