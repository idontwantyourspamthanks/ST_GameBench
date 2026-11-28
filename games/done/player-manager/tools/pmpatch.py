#!/usr/bin/env python3
"""Build patched Player Manager (PLAYERME) into build/game/."""
import shutil, struct, subprocess, sys
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

# Authentic 1989-90 English Football League kit colours for all 92 clubs.
# Verified Kick Off 2 styles (0..5):
#   0=Plain, 1=Stripes, 2=Chest Band/Hoops, 3=Contrasting Sleeves, 4=Shoulders/Yoke, 5=Diagonal Sash
# Verified Kick Off 2 20-colour palette (0..19):
#   0=Navy($005), 1=RoyalBlue($007), 2=SkyBlue($047), 3=Cyan($077), 4=White($777),
#   5=LtGrey($555), 6=DkGrey($444), 7=Black($000), 8=Claret($300), 9=DkRed($500),
#   10=Red($700), 11=Orange($730), 12=Yellow($770), 13=Pink($747), 14=Magenta($707),
#   15=Purple($307), 16=DkGreen($030), 17=Green($050), 18=Slate($245), 19=Teal($043)
TEAM_KITS_1989_90 = [
    # Division 1 (20)
    (3, 10, 4),  # ARSENAL          - Red w/ white sleeves
    (3, 8, 2),   # ASTON VILLA      - Claret w/ sky blue sleeves
    (0, 10, 4),  # CHARLTON         - Red & white
    (0, 1, 4),   # CHELSEA          - Royal blue & white
    (0, 2, 4),   # COVENTRY CITY    - Sky blue & white
    (1, 10, 1),  # CRYSTAL PALACE   - Red & blue stripes
    (0, 4, 7),   # DERBY COUNTY     - White & black
    (0, 1, 4),   # EVERTON          - Royal blue & white
    (0, 10, 10), # LIVERPOOL        - All red
    (0, 4, 11),  # LUTON TOWN       - White & orange
    (0, 2, 4),   # MANCHESTER CITY  - Sky blue & white
    (0, 10, 4),  # MANCHESTER UTD   - Red & white
    (0, 0, 4),   # MILLWALL         - Navy & white
    (0, 12, 17), # NORWICH CITY     - Yellow & green
    (0, 10, 4),  # NOTTM FOREST     - Red & white
    (2, 1, 4),   # Q.P.R.           - Blue & white band/hoops
    (1, 1, 4),   # SHEFFIELD WED    - Blue & white stripes
    (1, 10, 4),  # SOUTHAMPTON      - Red & white stripes
    (0, 4, 0),   # TOTTENHAM        - White & navy
    (0, 1, 12),  # WIMBLEDON        - Royal blue & yellow
    # Division 2 (24)
    (0, 10, 4),  # BARNSLEY         - Red & white
    (4, 1, 4),   # BLACKBURN        - Blue & white
    (1, 10, 7),  # BOURNEMOUTH      - Red & black stripes
    (1, 8, 12),  # BRADFORD CITY    - Claret & amber stripes
    (1, 1, 4),   # BRIGHTON         - Blue & white stripes
    (1, 11, 7),  # HULL CITY        - Amber & black stripes
    (0, 1, 4),   # IPSWICH TOWN     - Royal blue & white
    (0, 4, 12),  # LEEDS UNITED     - White & yellow
    (0, 1, 4),   # LEICESTER CITY   - Royal blue & white
    (0, 10, 4),  # MIDDLESBROUGH    - Red & white
    (1, 7, 4),   # NEWCASTLE UTD    - Black & white stripes
    (0, 1, 4),   # OLDHAM ATHLETIC  - Royal blue & white
    (0, 12, 0),  # OXFORD UNITED    - Yellow & navy
    (0, 16, 4),  # PLYMOUTH ARGYLE  - Dark green & white
    (0, 1, 4),   # PORTSMOUTH       - Royal blue & white
    (0, 4, 7),   # PORT VALE        - White & black
    (1, 10, 4),  # SHEFFIELD UTD    - Red & white stripes
    (1, 10, 4),  # STOKE CITY       - Red & white stripes
    (1, 10, 4),  # SUNDERLAND       - Red & white stripes
    (0, 10, 4),  # SWINDON TOWN     - Red & white
    (0, 12, 7),  # WATFORD          - Yellow & black
    (1, 0, 4),   # WEST BROMWICH    - Navy & white stripes
    (3, 8, 2),   # WEST HAM UTD     - Claret w/ sky blue sleeves
    (0, 11, 7),  # WOLVERHAMPTON    - Old gold & black
    # Division 3 (24)
    (0, 1, 4),   # BIRMINGHAM CITY  - Royal blue & white
    (0, 11, 4),  # BLACKPOOL        - Tangerine & white
    (0, 4, 0),   # BOLTON           - White & navy
    (1, 10, 4),  # BRENTFORD        - Red & white stripes
    (0, 10, 4),  # BRISTOL CITY     - Red & white
    (4, 1, 4),   # BRISTOL ROVERS   - Blue & white
    (0, 4, 0),   # BURY             - White & navy
    (0, 1, 4),   # CARDIFF CITY     - Royal blue & white
    (1, 1, 4),   # CHESTER CITY     - Blue & white stripes
    (0, 10, 4),  # CREWE ALEXANDRA  - Red & white
    (0, 4, 7),   # FULHAM           - White & black
    (1, 1, 4),   # HUDDERSFIELD     - Blue & white stripes
    (0, 10, 4),  # LEYTON ORIENT    - Red & white
    (0, 12, 1),  # MANSFIELD TOWN   - Amber & blue
    (0, 8, 4),   # NORTHAMPTON      - Claret & white
    (1, 7, 4),   # NOTTS COUNTY     - Black & white stripes
    (0, 4, 0),   # PRESTON          - White & navy
    (2, 1, 4),   # READING          - Blue & white band/hoops
    (3, 10, 4),  # ROTHERHAM UTD    - Red w/ white sleeves
    (1, 1, 12),  # SHREWSBURY       - Blue & amber stripes
    (0, 4, 7),   # SWANSEA CITY     - White & black
    (0, 4, 1),   # TRANMERE ROVERS  - White & blue
    (0, 10, 4),  # WALSALL          - Red & white
    (1, 1, 4),   # WIGAN ATHLETIC   - Blue & white stripes
    # Division 4 (24)
    (0, 10, 1),  # ALDERSHOT        - Red & blue
    (3, 8, 2),   # BURNLEY          - Claret w/ sky blue sleeves
    (0, 12, 7),  # CAMBRIDGE UTD    - Amber & black
    (0, 1, 4),   # CARLISLE UNITED  - Royal blue & white
    (0, 1, 4),   # CHESTERFIELD     - Royal blue & white
    (1, 1, 4),   # COLCHESTER UTD   - Blue & white stripes
    (2, 10, 4),  # DONCASTER        - Red & white band/hoops
    (1, 10, 4),  # EXETER CITY      - Red & white stripes
    (0, 1, 4),   # GILLINGHAM       - Royal blue & white
    (1, 7, 4),   # GRIMSBY TOWN     - Black & white stripes
    (0, 1, 4),   # HALIFAX TOWN     - Royal blue & white
    (1, 1, 4),   # HARTLEPOOL UTD   - Blue & white stripes
    (0, 4, 7),   # HEREFORD UNITED  - White & black
    (1, 10, 4),  # LINCOLN CITY     - Red & white stripes
    (0, 12, 7),  # MAIDSTONE UTD    - Yellow & black
    (0, 1, 4),   # PETERBOROUGH     - Royal blue & white
    (1, 1, 7),   # ROCHDALE         - Blue & black stripes
    (0, 10, 4),  # SCARBOROUGH      - Red & white
    (0, 8, 2),   # SCUNTHORPE UTD   - Claret & sky blue
    (0, 0, 4),   # SOUTHEND UNITED  - Navy & white
    (0, 1, 4),   # STOCKPORT        - Royal blue & white
    (0, 12, 1),  # TORQUAY UNITED   - Yellow & blue
    (0, 10, 4),  # WREXHAM          - Red & white
    (0, 10, 4),  # YORK CITY        - Red & white
]
assert len(TEAM_KITS_1989_90) == 92

# Authentic 1989-90 English Football League 2nd (Away) kits for all 92 clubs.
# Every away kit contrasts strongly with its club's home kit for automatic clash resolution!
TEAM_AWAY_KITS_1989_90 = [
    # Division 1 (20)
    (0, 12, 0),  # ARSENAL          - Yellow & navy
    (0, 4, 8),   # ASTON VILLA      - White & claret
    (0, 12, 7),  # CHARLTON         - Yellow & black
    (0, 4, 10),  # CHELSEA          - White & red
    (0, 12, 0),  # COVENTRY CITY    - Yellow & navy
    (0, 12, 1),  # CRYSTAL PALACE   - Yellow & blue
    (0, 1, 4),   # DERBY COUNTY     - Royal blue & white
    (0, 12, 1),  # EVERTON          - Yellow & blue
    (0, 5, 10),  # LIVERPOOL        - Silver/grey & red (iconic 89-90 away!)
    (0, 1, 11),  # LUTON TOWN       - Blue & orange
    (0, 8, 4),   # MANCHESTER CITY  - Maroon & white
    (0, 1, 4),   # MANCHESTER UTD   - Royal blue & white
    (0, 12, 0),  # MILLWALL         - Yellow & navy
    (0, 4, 17),  # NORWICH CITY     - White & green
    (0, 12, 1),  # NOTTM FOREST     - Yellow & blue
    (0, 10, 4),  # Q.P.R.           - Red & white
    (0, 12, 0),  # SHEFFIELD WED    - Yellow & navy
    (0, 12, 1),  # SOUTHAMPTON      - Yellow & blue
    (0, 12, 0),  # TOTTENHAM        - Yellow & navy
    (0, 12, 1),  # WIMBLEDON        - Yellow & blue
    # Division 2 (24)
    (0, 4, 10),  # BARNSLEY         - White & red
    (0, 10, 7),  # BLACKBURN        - Red & black
    (0, 12, 7),  # BOURNEMOUTH      - Yellow & black
    (0, 4, 8),   # BRADFORD CITY    - White & claret
    (0, 12, 1),  # BRIGHTON         - Yellow & blue
    (0, 4, 7),   # HULL CITY        - White & black
    (0, 12, 1),  # IPSWICH TOWN     - Yellow & blue
    (0, 12, 1),  # LEEDS UNITED     - Yellow & blue
    (0, 12, 1),  # LEICESTER CITY   - Yellow & blue
    (0, 2, 0),   # MIDDLESBROUGH    - Sky blue & navy
    (0, 12, 16), # NEWCASTLE UTD    - Yellow & green
    (0, 11, 1),  # OLDHAM ATHLETIC  - Tangerine & blue
    (0, 4, 0),   # OXFORD UNITED    - White & navy
    (0, 4, 16),  # PLYMOUTH ARGYLE  - White & dark green
    (0, 4, 1),   # PORTSMOUTH       - White & blue
    (0, 12, 7),  # PORT VALE        - Yellow & black
    (0, 12, 7),  # SHEFFIELD UTD    - Yellow & black
    (0, 2, 0),   # STOKE CITY       - Sky blue & navy
    (0, 1, 4),   # SUNDERLAND       - Royal blue & white
    (0, 4, 10),  # SWINDON TOWN     - White & red
    (0, 4, 7),   # WATFORD          - White & black
    (0, 12, 17), # WEST BROMWICH    - Yellow & green
    (0, 4, 8),   # WEST HAM UTD     - White & claret
    (0, 4, 7),   # WOLVERHAMPTON    - White & black
    # Division 3 (24)
    (0, 12, 1),  # BIRMINGHAM CITY  - Yellow & blue
    (0, 4, 11),  # BLACKPOOL        - White & tangerine
    (0, 10, 4),  # BOLTON           - Red & white
    (0, 12, 1),  # BRENTFORD        - Yellow & blue
    (0, 12, 7),  # BRISTOL CITY     - Yellow & black
    (0, 12, 1),  # BRISTOL ROVERS   - Yellow & blue
    (0, 1, 4),   # BURY             - Royal blue & white
    (0, 12, 1),  # CARDIFF CITY     - Yellow & blue
    (0, 12, 1),  # CHESTER CITY     - Yellow & blue
    (0, 4, 10),  # CREWE ALEXANDRA  - White & red
    (0, 10, 4),  # FULHAM           - Red & white
    (0, 12, 0),  # HUDDERSFIELD     - Yellow & navy
    (0, 2, 0),   # LEYTON ORIENT    - Sky blue & navy
    (0, 1, 4),   # MANSFIELD TOWN   - Royal blue & white
    (0, 4, 8),   # NORTHAMPTON      - White & claret
    (0, 12, 7),  # NOTTS COUNTY     - Yellow & black
    (0, 12, 0),  # PRESTON          - Yellow & navy
    (0, 12, 1),  # READING          - Yellow & blue
    (0, 12, 7),  # ROTHERHAM UTD    - Yellow & black
    (0, 4, 1),   # SHREWSBURY       - White & blue
    (0, 10, 4),  # SWANSEA CITY     - Red & white
    (0, 1, 4),   # TRANMERE ROVERS  - Royal blue & white
    (0, 17, 4),  # WALSALL          - Green & white
    (0, 12, 1),  # WIGAN ATHLETIC   - Yellow & blue
    # Division 4 (24)
    (0, 12, 1),  # ALDERSHOT        - Yellow & blue
    (0, 4, 8),   # BURNLEY          - White & claret
    (0, 4, 7),   # CAMBRIDGE UTD    - White & black
    (0, 10, 4),  # CARLISLE UNITED  - Red & white
    (0, 12, 1),  # CHESTERFIELD     - Yellow & blue
    (0, 12, 1),  # COLCHESTER UTD   - Yellow & blue
    (0, 12, 7),  # DONCASTER        - Yellow & black
    (0, 12, 7),  # EXETER CITY      - Yellow & black
    (0, 12, 1),  # GILLINGHAM       - Yellow & blue
    (0, 10, 4),  # GRIMSBY TOWN     - Red & white
    (0, 12, 1),  # HALIFAX TOWN     - Yellow & blue
    (0, 12, 1),  # HARTLEPOOL UTD   - Yellow & blue
    (0, 10, 4),  # HEREFORD UNITED  - Red & white
    (0, 12, 7),  # LINCOLN CITY     - Yellow & black
    (0, 4, 7),   # MAIDSTONE UTD    - White & black
    (0, 12, 1),  # PETERBOROUGH     - Yellow & blue
    (0, 12, 1),  # ROCHDALE         - Yellow & blue
    (0, 12, 7),  # SCARBOROUGH      - Yellow & black
    (0, 4, 8),   # SCUNTHORPE UTD   - White & claret
    (0, 12, 0),  # SOUTHEND UNITED  - Yellow & navy
    (0, 12, 1),  # STOCKPORT        - Yellow & blue
    (0, 1, 4),   # TORQUAY UNITED   - Royal blue & white
    (0, 4, 10),  # WREXHAM          - White & red
    (0, 12, 1),  # YORK CITY        - Yellow & blue
]
assert len(TEAM_AWAY_KITS_1989_90) == 92

def pack_kit_word(style: int, col1: int, col2: int) -> int:
    return 0x8000 | ((style & 7) << 10) | ((col1 & 31) << 5) | (col2 & 31)

def build():
    WORK.mkdir(parents=True, exist_ok=True)
    # Generate 92-team names, squad counts, and authentic 1989-90 home + away kits
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
        f.write("        even\nteam_kits_92:\n")
        for idx, (st, c1, c2) in enumerate(TEAM_KITS_1989_90):
            kw = pack_kit_word(st, c1, c2)
            f.write(f"        dc.w ${kw:04x} ; {TEAMS_1989_90[idx]}\n")
        f.write("team_away_kits_92:\n")
        for idx, (st, c1, c2) in enumerate(TEAM_AWAY_KITS_1989_90):
            kw = pack_kit_word(st, c1, c2)
            f.write(f"        dc.w ${kw:04x} ; {TEAMS_1989_90[idx]} away\n")
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
        demo_bytes = bytearray(demo_src.read_bytes())
        # Store default Home (Plain, Royal Blue & White) at -$24c8(a4) and Away (Plain, Yellow & Navy) at -$24c6(a4)
        hum_kit_off = 92 * 100 + 2600 * 42 + (0x2e70 - 0x24c8)
        assert demo_bytes[hum_kit_off:hum_kit_off+4] == b"\x00\x00\x00\x00", "unexpected non-zero bytes at -$24c8..-$24c5(a4) in DEMO92.DAT"
        struct.pack_into(">HH", demo_bytes, hum_kit_off, pack_kit_word(0, 1, 4), pack_kit_word(0, 12, 0))
        (BUILD / "FILES" / "DEMO92.DAT").write_bytes(demo_bytes)
        print(f"Copied 92-team {demo_src.name} (+ default 1st & 2nd club kits) into {BUILD / 'FILES'}")

    # Task 2: Copy Kick Off 2 engine binary, resident handler, KRD assets, and PM match segment
    assert 0xb3000 + len(payload) <= 0xb7700, f"payload overlaps BR_STATE: ${0xb3000 + len(payload):x}"
    ko2_orig = ROOT.parent.parent / "queue" / "kick-off-2" / "originals" / "KICKOFF2" / "FILES" / "KRD"
    ko2_ram = WORK / "ko2_ram.bin"
    pm_ram = WORK / "setup_ram.bin"
    if ko2_orig.exists() and ko2_ram.exists() and pm_ram.exists():
        ram = ko2_ram.read_bytes()
        (BUILD / "FILES" / "KO2ENG.BIN").write_bytes(ram[0x10000:0x24000])
        (BUILD / "FILES" / "KO2HND.BIN").write_bytes(ram[0x6800:0x7020])
        (BUILD / "FILES" / "PMCODE.BIN").write_bytes(pm_ram.read_bytes()[0x10000:0x25900])
        shutil.copy2(ko2_orig, BUILD / "FILES" / "KRD")
        print("Installed Kick Off 2 match engine overlay (KO2ENG.BIN + KO2HND.BIN + PMCODE.BIN + KRD)")

    # v1.1: Assemble Atari STE Amiga Audio & Visuals overlay (KO2STE.BIN) + Amiga DMA Audio (AMIGASND.BIN)
    ko2_ste_src = ROOT / "patches" / "ko2_ste.s"
    if ko2_ste_src.exists():
        ko2_ste_bin = assemble(ko2_ste_src, WORK / "ko2_ste.bin")
        assert len(ko2_ste_bin) <= 0x25c0, f"KO2STE.BIN too large: {len(ko2_ste_bin)} > 9664"
        (BUILD / "FILES" / "KO2STE.BIN").write_bytes(ko2_ste_bin)
        print(f"Assembled KO2STE.BIN: {len(ko2_ste_bin)} bytes")
    amiga_snd_src = WORK / "amiga" / "extracted" / "sounds"
    if amiga_snd_src.exists():
        raw_s = amiga_snd_src.read_bytes()
        tpos = len(raw_s) - 68
        offs = struct.unpack(">17I", raw_s[tpos:])
        PAL_CLK = 3546895.0
        TARGET_HZ = 6258.0
        DMA_MODE = 0x0080  # 6258 Hz mono signed 8-bit PCM
        # Keep total <= 22,500 bytes (comfortably inside KO2's $1c138 Malloc with >600 bytes margin!)
        MAX_LEN = {12: 6100, 13: 9000}
        hdr = bytearray()
        body = bytearray()
        hdr_size = 17 * 12  # 204 bytes (even)
        for i in range(17):
            o = offs[i]
            period, slen = struct.unpack(">HI", raw_s[o:o+6])
            pcm = raw_s[o+6 : o+6+slen]
            hz = PAL_CLK / period if period else TARGET_HZ
            out_len = max(2, int(round(slen * TARGET_HZ / hz)) & ~1) if slen > 8 else 2
            if i in MAX_LEN and out_len > MAX_LEN[i]:
                out_len = MAX_LEN[i]
            # Linear interpolation resample (signed 8-bit PCM)
            if slen <= 8:
                resamp = bytes([0, 0])
            else:
                out = bytearray(out_len)
                ratio = (slen - 1) / max(1, (int(round(slen * TARGET_HZ / hz)) & ~1) - 1)
                for j in range(out_len):
                    pos = j * ratio
                    k = int(pos)
                    frac = pos - k
                    s0 = pcm[k] - 256 if pcm[k] >= 128 else pcm[k]
                    s1 = pcm[min(k + 1, slen - 1)]
                    s1 = s1 - 256 if s1 >= 128 else s1
                    val = int(round(s0 + (s1 - s0) * frac))
                    # Smooth 64-sample fade-out if trimmed so zero click!
                    if i in MAX_LEN and j >= out_len - 64:
                        val = int(val * (out_len - 1 - j) / 64.0)
                    val = max(-128, min(127, val))
                    out[j] = val & 0xFF
                resamp = bytes(out)
            hdr.extend(struct.pack(">IIHH", hdr_size + len(body), len(resamp), DMA_MODE, 0))
            body.extend(resamp)
        amiga_snd_bin = bytes(hdr + body)
        assert len(amiga_snd_bin) <= 23346, f"AMIGASND.BIN exceeds ST SAMPLES.DAT: {len(amiga_snd_bin)}"
        (BUILD / "FILES" / "AMIGASND.BIN").write_bytes(amiga_snd_bin)
        print(f"Built AMIGASND.BIN: {len(amiga_snd_bin)} bytes (17 Amiga samples @ 6258 Hz STE DMA)")

    # v1.1: Convert all 4 Amiga pitches (nor, wet, sog, art) -> AMIGAP0..3.BIN (32,288 bytes each)
    # Format per file:
    #   +$0000 (   32 B): 8 STE 12-bit RGB pitch colours (0..7) + 8 pad words
    #   +$0020 ( 7680 B): 80x96 tilemap (0-based tile indices 0..255)
    #   +$1e20 (24576 B): 256 x (16x16 x 3bpp) tiles in ST interleaved word format (16 rows x 6 bytes)
    amiga_pit_src = WORK / "amiga" / "extracted" / "pitches.dat"
    if amiga_pit_src.exists():
        pdata = amiga_pit_src.read_bytes()
        phdr = struct.unpack(">I", pdata[:4])[0] + 4
        pentries = {}
        plist = []
        for off in range(4, phdr - 4, 16):
            ent = pdata[off:off+16]
            if ent[0] == 0:
                break
            name = ent[:12].split(b"\x00", 1)[0].decode("ascii", "replace")
            foff = struct.unpack(">I", ent[12:16])[0] + phdr
            plist.append((name, foff))
        for i, (name, foff) in enumerate(plist):
            end = plist[i+1][1] if i + 1 < len(plist) else len(pdata)
            pentries[name] = pdata[foff:end]

        def amiga4_to_ste4(v: int) -> int:
            # Atari STE 4-bit channel: bit 3 is LSB (bit 0 of 0..15), bits 2..0 are MSBs (bits 3..1)
            return ((v >> 1) & 7) | ((v & 1) << 3)

        def decode_ilbm_3bpp(buf: bytes):
            pos = 12
            w = h = npl = comp = 0
            cmap = []
            body = b""
            while pos < len(buf) - 8:
                cid = buf[pos:pos+4].decode("ascii", "replace")
                clen = struct.unpack(">I", buf[pos+4:pos+8])[0]
                cdata = buf[pos+8:pos+8+clen]
                if cid == "BMHD":
                    w, h, _x, _y, npl, _m, comp = struct.unpack(">HHhhBBB", cdata[:11])
                elif cid == "CMAP":
                    cmap = [(cdata[j] >> 4, cdata[j+1] >> 4, cdata[j+2] >> 4) for j in range(0, len(cdata), 3)]
                elif cid == "BODY":
                    body = cdata
                pos += 8 + clen + (clen & 1)
            row_bytes = ((w + 15) // 16) * 2
            if comp == 1:
                raw = bytearray()
                i = 0
                while i < len(body):
                    n = body[i]; i += 1
                    if n < 128:
                        raw.extend(body[i:i+n+1]); i += n + 1
                    elif n > 128:
                        raw.extend(bytes([body[i]]) * (257 - n)); i += 1
                body = bytes(raw)
            return w, h, npl, row_bytes, cmap, body

        for pidx, ext in enumerate(("nor", "wet", "sog", "art")):
            pmap_raw = pentries[f"pdat.{ext}"]
            mw, mh = struct.unpack(">HH", pmap_raw[:4])
            assert (mw, mh) == (80, 96)
            # Pre-subtract 1 so tile indices are 0..255!
            tilemap = bytes((b - 1) & 0xFF for b in pmap_raw[4:4+80*96])
            w, h, npl, row_bytes, cmap, body = decode_ilbm_3bpp(pentries[f"fbgraph4.{ext}"])
            assert w == 320 and npl == 3 and row_bytes == 40
            # Build 16-word STE palette header (0..7 = STE 12-bit Amiga pitch, 8..15 = 0)
            pal_bytes = bytearray()
            for c_i in range(8):
                r, g, b = cmap[c_i] if c_i < len(cmap) else (0, 0, 0)
                ste_rgb = (amiga4_to_ste4(r) << 8) | (amiga4_to_ste4(g) << 4) | amiga4_to_ste4(b)
                pal_bytes.extend(struct.pack(">H", ste_rgb))
            pal_bytes.extend(b"\x00" * 16)
            # Extract 256 tiles (16x16x3bpp) in ST interleaved word format (row y: p0.w, p1.w, p2.w)
            tiles_bytes = bytearray(256 * 96)
            max_tiles = (h // 16) * 20
            for tid in range(min(256, max_tiles)):
                col = tid % 20
                row = tid // 20
                dst = tid * 96
                for y in range(16):
                    src_y = (row * 16 + y) * (3 * row_bytes)
                    p0 = struct.unpack(">H", body[src_y + 0*row_bytes + col*2 : src_y + 0*row_bytes + col*2 + 2])[0]
                    p1 = struct.unpack(">H", body[src_y + 1*row_bytes + col*2 : src_y + 1*row_bytes + col*2 + 2])[0]
                    p2 = struct.unpack(">H", body[src_y + 2*row_bytes + col*2 : src_y + 2*row_bytes + col*2 + 2])[0]
                    struct.pack_into(">HHH", tiles_bytes, dst + y * 6, p0, p1, p2)
            out_pit = bytes(pal_bytes) + tilemap + bytes(tiles_bytes)
            assert len(out_pit) == 32 + 7680 + 24576
            (BUILD / "FILES" / f"AMIGAP{pidx}.BIN").write_bytes(out_pit)
        print("Built AMIGAP0..3.BIN: 4 Amiga STE pitches (32,288 bytes each: STE 12-bit pal + 80x96 map + 256 3bpp tiles)")

    # Patch HAGA: pp_nofade (remove grey fade on saves/loads) + pp_bigram_cache (4MB+ safe for $b3000)
    # + clamp HAGA's $424-derived RAM units against phystop ($42e >> 19) so MiSTerFPGA MEM1M + TOS 1.62
    # ($424=$08 while $42e=$100000) never relocates HAGA into unmapped $1f8000 (3-bomb Address Error!).
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
        # pp_phystop_ram: read tested phystop>>19 ($2(a0), from $42e.w) instead of $424.w bank config ($7(a0))
        # so MiSTerFPGA MEM1M + TOS 1.62 ($424=$08, $42e=$100000) relocates HAGA to $0f8000 instead of $1f8000!
        (0x21a0, "12a80007", "12a80002"),
    ]
    # Assemble exact bytes for pp_nofade $1460..$1483
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

    # Assemble 32-bit-clean HAGA $014c..$0199 (78 bytes): preserve upper words of d1/d2/d3/d4 = 0
    # and clamp $424-derived 512KB units d3 <= -1(a2) (phystop>>19) so BOTH RUNME.TOS and HAGA
    # relocate HAGA to $0f8000 (never unmapped $1f8000!) on MiSTerFPGA MEM1M + TOS 1.62 ($424=$08).
    haga_ram_orig = (
        "428316380424240302020001220302010004e409d401"
        "280302040002220302010008e409d801e20c42834a02"
        "6708263c00040000e5ab42824a04670a243c00100000"
        "e9aad6824843e64b15430004"
    )
    haga_ram_src = WORK / "haga_ram_clamp.s"
    haga_ram_src.write_text("""
        org     $014c
        moveq   #0,d3
        move.b  $424.w,d3
        move.l  d3,d2
        andi.b  #1,d2
        move.l  d3,d1
        andi.b  #4,d1
        lsr.b   #2,d1
        add.b   d1,d2
        move.l  d3,d4
        andi.b  #2,d4
        move.l  d3,d1
        andi.b  #8,d1
        lsr.b   #2,d1
        add.b   d1,d4
        lsr.b   #1,d4
        moveq   #0,d3
        tst.b   d2
        beq.s   .b1
        moveq   #1,d3
        subq.b  #1,d2
        lsl.b   d2,d3
.b1:    moveq   #0,d2
        tst.b   d4
        beq.s   .cl
        moveq   #2,d2
        lsl.b   d4,d2
        add.b   d2,d3
.cl:    cmp.b   -1(a2),d3
        bls.s   .ok
        move.b  -1(a2),d3
.ok:    move.b  d3,4(a2)
""")
    haga_ram_new = assemble(haga_ram_src, WORK / "haga_ram_clamp.bin")
    assert len(haga_ram_new) <= 78 and len(haga_ram_new) % 2 == 0
    haga_ram_new += b"\x4e\x71" * ((78 - len(haga_ram_new)) // 2)
    haga_edits.append((0x014c, haga_ram_orig, haga_ram_new.hex()))

    for off, orig_hex, new_hex in haga_edits:
        orig = bytes.fromhex(orig_hex)
        new = bytes.fromhex(new_hex)
        assert len(orig) == len(new)
        assert haga[off:off+len(orig)] == orig, f"HAGA+{off:#x} mismatch: {haga[off:off+len(orig)].hex()} != {orig_hex}"
        haga[off:off+len(new)] = new
    haga_path.write_bytes(haga)
    print(f"Patched {haga_path} (pp_nofade + pp_bigram_cache + ram_clamp)")

if __name__ == "__main__":
    build()
