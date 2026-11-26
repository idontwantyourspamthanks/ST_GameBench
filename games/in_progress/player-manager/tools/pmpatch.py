#!/usr/bin/env python3
"""Build patched Player Manager (PLAYERME) into build/game/."""
import shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORIG = ROOT / "originals" / "PLAYERME"
BUILD = ROOT / "build" / "game"
PATCH_SRC = ROOT / "patches" / "micro_opt.s"
WORK = ROOT / "work"

def assemble(src: Path, out: Path) -> bytes:
    subprocess.run(
        ["vasmm68k_mot", "-Fbin", "-m68000", "-quiet", "-o", str(out), str(src)],
        check=True,
    )
    return out.read_bytes()

# Authentic 1989-90 English Football League (92 clubs: 20 + 24 + 24 + 24)
# Kept <= 15 chars to fit all original Player Manager UI text boxes cleanly.
TEAMS_1989_90 = [
    # Division 1 (20)
    "ARSENAL", "ASTON VILLA", "CHARLTON", "CHELSEA", "COVENTRY CITY",
    "CRYSTAL PALACE", "DERBY COUNTY", "EVERTON", "LIVERPOOL", "LUTON TOWN",
    "MANCHESTER CITY", "MANCHESTER UTD", "MILLWALL", "NORWICH CITY", "NOTTM FOREST",
    "Q.P.R.", "SHEFFIELD WED", "SOUTHAMPTON", "TOTTENHAM", "WIMBLEDON",
    # Division 2 (24)
    "BARNSLEY", "BLACKBURN", "BOURNEMOUTH", "BRADFORD CITY", "BRIGHTON",
    "HULL CITY", "IPSWICH TOWN", "LEEDS UNITED", "LEICESTER CITY", "MIDDLESBROUGH",
    "NEWCASTLE UTD", "OLDHAM ATHLETIC", "OXFORD UNITED", "PLYMOUTH ARGYLE", "PORTSMOUTH",
    "PORT VALE", "SHEFFIELD UTD", "STOKE CITY", "SUNDERLAND", "SWINDON TOWN",
    "WATFORD", "WEST BROMWICH", "WEST HAM UTD", "WOLVERHAMPTON",
    # Division 3 (24)
    "BIRMINGHAM CITY", "BLACKPOOL", "BOLTON", "BRENTFORD", "BRISTOL CITY",
    "BRISTOL ROVERS", "BURY", "CARDIFF CITY", "CHESTER CITY", "CREWE ALEXANDRA",
    "FULHAM", "HUDDERSFIELD", "LEYTON ORIENT", "MANSFIELD TOWN", "NORTHAMPTON",
    "NOTTS COUNTY", "PRESTON", "READING", "ROTHERHAM UTD", "SHREWSBURY",
    "SWANSEA CITY", "TRANMERE ROVERS", "WALSALL", "WIGAN ATHLETIC",
    # Division 4 (24)
    "ALDERSHOT", "BURNLEY", "CAMBRIDGE UTD", "CARLISLE UNITED", "CHESTERFIELD",
    "COLCHESTER UTD", "DONCASTER", "EXETER CITY", "GILLINGHAM", "GRIMSBY TOWN",
    "HALIFAX TOWN", "HARTLEPOOL UTD", "HEREFORD UNITED", "LINCOLN CITY", "MAIDSTONE UTD",
    "PETERBOROUGH", "ROCHDALE", "SCARBOROUGH", "SCUNTHORPE UTD", "SOUTHEND UNITED",
    "STOCKPORT", "TORQUAY UNITED", "WREXHAM", "YORK CITY",
]
assert len(TEAMS_1989_90) == 92
assert all(len(t) <= 15 for t in TEAMS_1989_90)

SQUAD_BY_DIV = [
    (2, 7, 7, 5),  # Div 1 (20 x 21 = 420)
    (2, 6, 6, 5),  # Div 2 (24 x 19 = 456)
    (2, 6, 6, 4),  # Div 3 (24 x 18 = 432)
    (2, 6, 5, 4),  # Div 4 (24 x 17 = 408) -> total 1,716
]

def build():
    WORK.mkdir(parents=True, exist_ok=True)
    # Generate 92-team names & squad counts
    with (WORK / "league92_data.inc").open("w") as f:
        f.write("team_names_92:\n")
        for name in TEAMS_1989_90:
            raw = name.encode("ascii") + b"\x00" * (20 - len(name))
            vals = ",".join(str(b) for b in raw)
            f.write(f"        dc.b {vals} ; {name}\n")
        f.write("squad_counts_92:\n")
        for idx in range(92):
            div = 0 if idx < 20 else (1 if idx < 44 else (2 if idx < 68 else 3))
            k, d, m, fw = SQUAD_BY_DIV[div]
            f.write(f"        dc.b {k},{d},{m},{fw}\n")
    # Generate exact lookup tables included by micro_opt.s
    with (WORK / "luts.inc").open("w") as f:
        f.write("tbl_1333:\n")
        for i in range(0, 256, 16):
            vals = ",".join(str((x * 1333) // 1000) for x in range(i, i + 16))
            f.write(f"        dc.w {vals}\n")
        f.write("tbl_1750:\n")
        for i in range(0, 256, 16):
            vals = ",".join(str((x * 1000) // 1750) for x in range(i, i + 16))
            f.write(f"        dc.b {vals}\n")
    payload = assemble(PATCH_SRC, WORK / "micro_opt.bin")
    # Pad payload to multiple of 4 bytes
    if len(payload) % 4:
        payload += b"\x00" * (4 - len(payload) % 4)
    payload_longs = len(payload) // 4
    print(f"Assembled micro_opt.s: {len(payload)} bytes ({payload_longs} longs)")

    # Assemble tiny PC-relative stager at PMLA+$eed2 (copies payload at PMLA+$f000 to $b3000)
    stager_src = WORK / "stager.s"
    stager_src.write_text(f"""
        org $eed2
stager:
        lea     $f000(pc),a0
        lea     $b3000.l,a2
        move.w  #{payload_longs - 1},d2
.cp:
        move.l  (a0)+,(a2)+
        dbra    d2,.cp
        suba.l  #($eed2-$00a2),a1
        lea     ($0090-$00a2)(a1),a0
        jmp     (a0)
""")
    stager = assemble(stager_src, WORK / "stager.bin")
    assert len(stager) <= (0xf000 - 0xeed2), f"stager too big: {len(stager)}"
    print(f"Assembled stager: {len(stager)} bytes")

    # Copy originals/PLAYERME to build/game
    if BUILD.exists():
        shutil.rmtree(BUILD)
    shutil.copytree(ORIG, BUILD)

    pmla_path = BUILD / "FILES" / "PMLA"
    pmla = bytearray(pmla_path.read_bytes())

    # Verify original bytes in PMLA (file offset = 28 + text_offset)
    HDR = 28
    # 008c: lea $a2(pc),a1 (43fa 0014)
    assert pmla[HDR + 0x8c : HDR + 0x90] == bytes.fromhex("43fa0014"), \
        f"unexpected bytes at PMLA+$8c: {pmla[HDR+0x8c:HDR+0x90].hex()}"
    # 01de: jmp $10000.l (4ef9 0001 0000)
    assert pmla[HDR + 0x1de : HDR + 0x1e4] == bytes.fromhex("4ef900010000"), \
        f"unexpected bytes at PMLA+$1de: {pmla[HDR+0x1de:HDR+0x1e4].hex()}"
    # Verify data space at $eed2..$f000+len(payload) is all zeroes
    assert all(b == 0 for b in pmla[HDR + 0xeed2 : HDR + 0xf000 + len(payload)]), \
        "non-zero bytes in PMLA data target region!"

    # Patch 008c -> jmp (a1) ; nop (4ed1 4e71)
    pmla[HDR + 0x8c : HDR + 0x90] = bytes.fromhex("4ed14e71")
    # Patch 01de -> jmp $b3000.l (4ef9 000b 3000)
    pmla[HDR + 0x1de : HDR + 0x1e4] = bytes.fromhex("4ef9000b3000")
    # Write stager at $eed2 and payload at $f000
    pmla[HDR + 0xeed2 : HDR + 0xeed2 + len(stager)] = stager
    pmla[HDR + 0xf000 : HDR + 0xf000 + len(payload)] = payload

    pmla_path.write_bytes(pmla)
    print(f"Wrote patched {pmla_path} ({len(pmla)} bytes)")

    demo_src = WORK / "DEMO92.DAT"
    if demo_src.exists():
        shutil.copy2(demo_src, BUILD / "FILES" / "DEMO92.DAT")
        print(f"Copied 92-team {demo_src.name} into {BUILD / 'FILES'}")

    # Task 2: Copy Kick Off 2 engine binary, resident handler, KRD assets, and PM match segment
    assert 0xb3000 + len(payload) <= 0xb5800, f"payload overlaps BR_STATE: ${0xb3000 + len(payload):x}"
    ko2_orig = ROOT.parent.parent / "queue" / "kick-off-2" / "originals" / "KICKOFF2" / "FILES" / "KRD"
    ko2_ram = WORK / "ko2_ram.bin"
    pm_ram = WORK / "setup_ram.bin"
    if ko2_orig.exists() and ko2_ram.exists() and pm_ram.exists():
        ram = ko2_ram.read_bytes()
        (BUILD / "FILES" / "KO2ENG.BIN").write_bytes(ram[0x10000:0x24000])
        (BUILD / "FILES" / "KO2HND.BIN").write_bytes(ram[0x6800:0x7020])
        (BUILD / "FILES" / "PMMATCH.BIN").write_bytes(pm_ram.read_bytes()[0x18e80:0x2169c])
        shutil.copy2(ko2_orig, BUILD / "FILES" / "KRD")
        print("Installed Kick Off 2 match engine overlay (KO2ENG.BIN + KO2HND.BIN + PMMATCH.BIN + KRD)")

    # Patch HAGA: pp_nofade (remove grey fade on saves/loads) + pp_bigram_cache (4MB+ safe for $b3000)
    haga_path = BUILD / "HAGA"
    haga = bytearray(haga_path.read_bytes())
    haga_edits = [
        # pp_nofade (verified against HAGA md5 b34607ed...)
        (0x0ffc, "61000168", "6100027a"),  # bsr.w $1278
        (0x16d8, "6100fa8c", "6100fb9e"),  # bsr.w $1278
        (0x1460,
         "43fa004622b8007045fafe3821ca007046fc2300323a003643fa003e30015240eb48d2c0",
         "103a0b2867402f38007045fafe3621ca0070323a00363001eb4843fb006446fc23004e71"),
        (0x149c, "46fc270021fa000600704e75", "46fc270021df00704e714e75"),
        # pp_bigram_cache: keep chunked cache on >=4MB 68000 machines so $b3000 isn't overwritten
        (0x3228, "2412", "602a"),
    ]
    # Assemble exact bytes for pp_nofade $1460..$1483? Verify with vasm to be 100% certain!
    nofade_src = WORK / "haga_nofade.s"
    nofade_src.write_text("""
HB      equ     0
        org     HB+$1460
        move.b  HB+$1f8a(pc),d0
        beq.s   HB+$14a6
        move.l  $70.w,-(a7)
        lea     HB+$12a2(pc),a2
        move.l  a2,$70.w
        move.w  HB+$14ac(pc),d1
        move.w  d1,d0
        lsl.w   #5,d0
        lea     HB+$14d8(pc,d0.w),a1
        move    #$2300,sr
        nop
""")
    nf_bytes = assemble(nofade_src, WORK / "haga_nofade.bin")
    assert len(nf_bytes) == 36, f"unexpected nf_bytes len: {len(nf_bytes)}"
    haga_edits[2] = (0x1460, haga_edits[2][1], nf_bytes.hex())

    for off, orig_hex, new_hex in haga_edits:
        orig = bytes.fromhex(orig_hex)
        new = bytes.fromhex(new_hex)
        assert len(orig) == len(new)
        assert haga[off:off+len(orig)] == orig, f"HAGA+{off:#x} mismatch: {haga[off:off+len(orig)].hex()} != {orig_hex}"
        haga[off:off+len(new)] = new
    haga_path.write_bytes(haga)
    print(f"Patched {haga_path} (pp_nofade + pp_bigram_cache)")

if __name__ == "__main__":
    build()
