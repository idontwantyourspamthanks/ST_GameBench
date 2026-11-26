; name: rd_init
; default: yes
; site: $78f6
; orig: 4eb90000fde0
; requires: rd_geom rd_draw
; doc: Road tables at race load time (part 3 of 3 of the faster road, needs rd_geom and rd_draw): the one-off table generation (about 18 VBL) runs while the race is being set up instead of in the first road frame.
; note: Moonshine Racers road study (work/notes/road.md section 7.1, work/notes/integration.md).  rd_geom and rd_draw build their tables lazily on the first road frame (geometry product table 0.9 M cycles, window tables 2.0 M cycles =
; note: about 18 VBL at 8 MHz), which is a visible hitch at the start of the race and would show up as one late pass in the fixed-tick pacer.  Site $78f6: `jsr $fde0.l` in the game's race setup ($7860-$792c: it sets the colour table
; note: pointer $135a at $7890, builds the static tables $4564 $4644 $4ff8 at $78d2-$78f0 and then runs the ring generator initialisers).  This is the first point at which every input of the generators exists and it is before the
; note: race loop ($7a88), so the pacer never sees the work.  The blob replays the displaced `jsr $fde0.l`, then calls the two pre-warm entries ($B4000 rd_geom, $B5000 rd_draw): the same generators, with the same inputs,
; note: that the first road frame would run (each is a no-op when its tables already match, so a second call or a level change just regenerates what changed); the lazy paths in rd_geom/rd_draw stay as the fallback.
        org     $78f6
        jsr     $B6000.l

        org     $B6000
rd_init:
        jsr     $fde0.l                 ; the displaced call
        jsr     $B4000.l                ; rd_geom: static tables + product table
        jsr     $B5000.l                ; rd_draw: window tables
        rts
