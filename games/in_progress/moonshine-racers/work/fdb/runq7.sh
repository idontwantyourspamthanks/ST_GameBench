cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
F=work/fdb/fdb.py
O=work/fdb/out
V0=work/fdb/build_v0; V1=work/fdb/build_v1; V2=work/fdb/build_v2
c() { # name build machineargs... 
  n=$1; b=$2; shift 2
  python3 $F $n $b/disk_a.st $b/disk_b.st swapA --presses 3 --tail 30 "$@" > $O/$n.out 2>&1
}
# V2 matrix, STE 1 MB
c v2_blank_ste $V2 --tos 1.62 --bkind blank --vars bb52e
c v2_junk_ste  $V2 --tos 1.62 --bkind junk --vars bb52e
c v2_disk1_ste $V2 --tos 1.62 --bkind disk1 --vars bb52e
# V0 / V1 references, STE
c v0_empty_ste $V0 --tos 1.62
c v1_nob_ste   $V1 --tos 1.62 --nob
c v1_junk_ste  $V1 --tos 1.62 --bkind junk
# ST TOS 1.04
c v0_empty_st  $V0 --machine st --tos 1.04
c v2_nob_st    $V2 --machine st --tos 1.04 --nob --vars bb52e
c v2_empty_st  $V2 --machine st --tos 1.04 --vars bb52e
c v2_blank_st  $V2 --machine st --tos 1.04 --bkind blank --vars bb52e
c v2_junk_st   $V2 --machine st --tos 1.04 --bkind junk --vars bb52e
c v2_disk1_st  $V2 --machine st --tos 1.04 --bkind disk1 --vars bb52e
c v1_empty_st  $V1 --machine st --tos 1.04
