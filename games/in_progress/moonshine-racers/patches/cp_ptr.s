; name: cp_ptr
; default: yes
; site: $fda2
; orig: 41f900058c00
; gate: ram2mb
; requires: cp_wrap cp_title cp_fetch cp_end cp_start cp_hiscore
; doc: Campaigns, stream setup: the track block is parsed where cp_fetch put it.
; note: Campaign feature (HD and floppy builds).  Site $fda2 = the first instruction of the track stream setup, `lea.l $58c00.l,a0` -> `movea.l CPV+8.l,a0` (6 bytes either way): the five stream pointers and the object pointer
; note: ($23c0 $1bb0 $1bb4 $27da $133a $1342) are derived from a0 and are 32-bit clean everywhere (work/notes/trackloader.md section 4.1, 11.1); PTR is $58c00 without a campaign (set by cp_fetch).
        org     $fda2
        movea.l CPV+8.l,a0
