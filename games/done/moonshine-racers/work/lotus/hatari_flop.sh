#!/bin/bash
# wrapper: drop the harness' --harddrive/--auto options, boot floppy A: (read-only) from $LOTUS_DISK
args=()
while [ $# -gt 0 ]; do
  case "$1" in
    --harddrive|--auto) shift 2;;
    *) args+=("$1"); shift;;
  esac
done
exec hatari "${args[@]}" --disk-a "$LOTUS_DISK" --protect-floppy on
