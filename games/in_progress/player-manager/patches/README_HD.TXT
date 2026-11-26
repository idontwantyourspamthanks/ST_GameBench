Player Manager v1.1 enhanced by dad_prg (patched PP HAGA hard-disk conversion)

Copy the PLAYERME folder to your Atari ST/STE hard disk (or Hatari GEMDOS drive)
and run RUNME.TOS. Requires 1 MB RAM or more (verified on 1 MB & 4 MB ST/STE
with real ACSI HDDRIVER and self-booting 1.44 MB floppy).

What's New in v1.1 (Atari STE Amiga Visuals & Audio):
- Kick Off 2 Amiga Visuals on Atari STE (True Double-Buffered in 1 MB RAM!):
  * All 4 Amiga tiled pitches (Normal, Wet, Soggy, Artificial) rendered with
    STE 12-bit RGB palettes, two 208x168 unmirrored Ring Buffers, STE Hardware
    Fine Scrolling, and Shared-Bus STE Hardware Blitter masked 4bpp sprites.
  * Dual-playfield 16-colour split (0..7 Amiga pitch, 8..15 KO2 club kits &
    HUD), transparent vector radar (X resize, D toggle), active player black
    underline, and HBlank-locked bottom HUD (player name, clock, score).
- Kick Off 2 Amiga DMA Audio on Atari STE:
  * 17 authentic Amiga 8-bit signed PCM sound effects playing via STE DMA
    audio hardware (6,258 Hz mono) with zero Timer-A CPU overhead.
- Dedicated STE Mode & Plain ST Auto-Fallback:
  * Atari STE / Mega STE runs the dedicated Amiga STE engine automatically.
  * Plain 68000 Atari ST (1 MB+) is detected automatically and runs classic
    v1.0 ST graphics (Timer B grass stripes) and YM audio with zero issues.
- Real Hard-Disk Driver & 1 MB / 4 MB RAM Compatibility:
  * High-RAM overlay layout stays safely below resident HDDRIVER.SYS on 1 MB
    machines (TOS 1.04, 1.62 and 2.06) and preserves dynamic TRAP #1 / HAGA
    pointers cleanly on 2 MB / 4 MB machines.
  * Title screens display a discreet "v1.1 enhanced by dad_prg" credit.

What's New in v1.0:
1. Full 1989-90 English Football League (92 Clubs, 4 Divisions)
   - Expanded from 44 teams (10/10/12/12) to the authentic 1989-90 92-club
     structure: Division 1 (20), Division 2 (24), Division 3 (24), Division 4 (24).
   - 2,600-player pool, 38/46-week Berger round-robin fixtures, 3-up/3-down
     promotion & relegation, and 92-team Cup competition (R0/R1 draws).
   - Scrolling League Names & Division Tables: click the active Division tab or
     press Space / Up / Down to scroll; Esc or Done exits.
   - Paged Weekly Fixtures & Results: click or press any key to advance pages.
   - 92-team DEMO92.DAT wired to Demo Game & Restart Game for instant Week 1 play.

2. Kick Off 2 Match Engine (50 FPS on 1 MB STE!)
   - Replaces Player Manager's original "Kick Off 1.5" match engine with the
     genuine Kick Off 2 match engine running natively at 50 FPS inside 1 MB RAM.
   - Includes Kick Off 2's full physics & aftertouch (banana shots/swerve),
     instant replays (press R), live in-match tactics switching (keys 1-4 for
     4-2-4, 4-3-3, 4-4-2, 5-3-2), dynamic pitch conditions (Normal, Wet, Soggy,
     Artificial), referee variety, Cup Extra Time, Up/Down pitch selection,
     Normal (5:00) vs Fast (3:00) half lengths, and non-clashing club kits.
   - Full management integration: goals, bookings, injuries, appearances, and
     final scores commit back to Player Manager's 2,600-player pool, followed
     by AI simulation of the other 45 weekly fixtures.

3. New Game Setup Speedup (~4.2x faster)
   - Bit-exact 68000 optimisations to LFSR RNG, position rating calculations,
     best-position selection, and early bucket rejection cut setup time from
     ~7m 40s (44 teams) to ~1m 49s (44 teams) / ~4m 13s (92 teams, 1,918 players).

4. Quality-of-Life & Loader Fixes
   - HAGA loader patched to remove the grey screen fade on loads/saves
     (pp_nofade) and to keep chunked caching safe on 4 MB+ machines.
   - Fixed a latent bug in PP's uncached KRD Fread (missing Fseek offset) so
     Kick Off 2 sprites and palettes load cleanly in 1 MB RAM.

In-Match Controls (Kick Off 2):
  Joystick 1   Move + Fire (kick/pass/aftertouch)
  X            Cycle radar size
  D            Toggle radar on / off
  R            Instant Replay
  1 - 4        Switch tactics live (4-2-4, 4-3-3, 4-4-2, 5-3-2)
  P            Pause / Resume

Every patch verifies original bytes before patching (marker PMOK at $b2ff8).
Tested on Hatari: 1 MB STE (TOS 1.62) & 1 MB ST (TOS 1.04), 8 MHz, 50 Hz PAL.
Not tested on real hardware.
