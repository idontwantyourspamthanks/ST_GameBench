#!/usr/bin/env bash
# Play the patched Midwinter 2 on an emulated Atari TT030 (32 MHz 68030) in Hatari.
#
#   tools/play-tt.sh               # patched build, TT, 2 MB ST-RAM
#   tools/play-tt.sh --original    # unpatched, for comparison (it runs too fast on a TT)
#   tools/play-tt.sh --ram 4096    # more ST-RAM (KiB)
#
# TOS: tos/TOS_3_06.img if you add one, otherwise EmuTOS (Atari never shipped a
# TT TOS image with this project). Other options as for tools/play.sh.
exec "$(dirname "${BASH_SOURCE[0]}")/play.sh" --machine tt --mmu true --ram 2048 "$@"
