# Powermonger intake notes

Source: `/home/ryan/Code/AtariST/powermonger/` (7 images, copied unchanged to `disks/`). Nothing here has been analysed for performance.

## 1. Disk geometry and file systems

Every image has the same BPB: 512 B/sector, 2 sectors/cluster, 1 reserved sector, 2 FATs, 112 root entries, 1600 sectors, media `$F9`, 10 sectors/track, 2 sides. That is 80 tracks x 2 x 10 x 512 = 819200 bytes. All are GEMDOS FAT12 disks; none is a custom trackloader layout.
Sectors per FAT: 3 in `007`, 5 in the others.

| Image | Size | Extra bytes after 819200 |
|---|---|---|
| `empire.st` | 829440 | 10240 (track 80, both sides, so 81 tracks). 3698 of the bytes are zero and the rest is leftover data, not referenced by the FAT. |
| `replicants_t2.st` | 820224 | 1024, all zero |
| the other five | 819200 | none |

mtools quirk: in every image except `007` the FAT's first byte is `$F7` while the BPB says `$F9`, so plain `mdir`/`mcopy` refuse it ("Bad media types f7/f9"). Setting `MTOOLS_SKIP_CHECK=1` is enough; no geometry options were needed:

    MTOOLS_SKIP_CHECK=1 mcopy -s -m -n -i disks/<v>.st :: extracted/<v>/

### Boot sectors (executable = word sum is `$1234`)

| Image | Executable | Content |
|---|---|---|
| `protected` | yes, `601c` | OEM `60hz`. Prints "Boot 60hz III is on the disk" / "Memory is not clear, perhaps virus", resets the TOS vectors and returns. A boot-sector utility; it does not load the game. TOS then runs `\AUTO\WAR.PRG`. |
| `007` | no (`601c` but sum `$ECBA`) | Random-looking serial, looks like a code stub from an old boot. The game is started by hand: `POWERMON.PRG`. `DESKTOP.INF` has no autorun entry. |
| `empire`, `empire_t`, `empire_t_b` | no | All zero apart from the BPB. TOS runs `\AUTO\WARI.PRG`. |
| `replicants` | yes, `6038` | TDT/Altair anti-virus check ("CHECK OK"), then `AUTO\POWER.PRG` runs. |
| `replicants_t2` | yes, `601c` | Small stub at `$1C`. |

## 2. Contents and differences

Common to all: `DATA/` with CAPGRAPH, END, END_PIC1, FX, LOSE, MAP, MAPDATA, QAZ, SPRITE8/16/24/32/40, TEXTURES, WIN (`.DAT`). The sizes are 3.9 KB to 138 KB. All are identical across variants except `SPRITE40.DAT` (see README).

| Variant | Files besides `DATA/` | What the crack changed |
|---|---|---|
| `protected` | `AUTO/WAR.PRG` 286384 | Nothing: this is the original program. |
| `007` | `POWERMON.007` 286384, `POWERMON.PRG` 25667, `POWERMON.TXT`, `README.TXT`, `DESKTOP.INF` | `POWERMON.007` is byte-identical to `protected/AUTO/WAR.PRG`. `POWERMON.PRG` is the loader that has to be double-clicked (it prints "Depack Error - Check Disk!!!", credits Jacky of ACF for sound, and runs `RMON.007`). `README.TXT` says the game needs about 25 s to unpack, so the loader depacks `POWERMON.007` at start. The files must be on `A:` in the root. German manual in `POWERMON.TXT`. |
| `empire` family | `AUTO/WARI.PRG` 293673 | `WARI.PRG` = a 7284-byte wrapper (Yoda's cracktro "Empire", then a `TRAINER (Y/N)?` prompt through `Crawcin`) followed by the original `WAR.PRG` byte for byte (offset 7284, 286384 bytes, zero differences) and 5 trailing bytes. So the trainer prompt is in all three Empire disks. `SPRITE40.DAT` is a different, larger file (137816 B). |
| `empire_t` vs `empire` | | `SPRITE40.DAT` differs in 3288 bytes inside `$1F400..$205FF`; boot-sector serial differs. [INFERENCE] this is where the trainer variant stores its patch/data. |
| `empire_t_b` vs `empire` | | None in the first 819200 bytes. `[b]` is the same content as the 81-track `empire.st`, minus the stray track. [INFERENCE] the fix is on the extra track, or the image only got re-dumped. |
| `replicants` | `WAR` 278624, `MREP` 6524, `AUTO/POWER.PRG` 3135 | `POWER.PRG` (text "If you rip my work, i will rip off your head ! (Illegal)") loads `a:\war` and `a:\mrep`. Both are Pack-Ice packed: `WAR` header `Ice!`, packed 278624, original 357010; `MREP` `Ice!` packed 6524, original `$7D22`. The depacked WAR is bigger than the 286384-byte original, so it is a different build (older, file dates 1986-04-24). It has not been unpacked here. |
| `replicants_t2` | `AUTO/WAR.DAT` 286384, `AUTO/INTRO.PRG` 1754 | `WAR.DAT` = original `WAR.PRG` with 4 bytes changed (file offsets `$27`, `$29`, `$204`, `$205`: `$40`->`$44`, `$0F`->`$0D`, `$4E`->`$4A`, `$75`->`$FC`). The first two change the opening palette-clear loop (it now starts at `$FF8244`, 14 entries), so it is a cosmetic hook for the intro. The other two are inside the encoded body. `INTRO.PRG` is packed with Automation Packer v2.3r. [INFERENCE] the `+2` is the trainer (extra lives). |

### Packer / protection of the main program

- Original `WAR.PRG` (286384 B, `601a` header, text `$45E90`, no symbols, relocation table at the end): no known signature found (no `ICE!`, `ATM5`, `LSD!`, `AU5!`, `PP20`; the lone `AUT`/`PP20` byte hits in other files are noise). It begins with a hand-written stub: `Super`, clear palette, copy a loader to `$500`, jump to `$508`. The rest compresses only to ~96 % with zlib, so the body is encoded or depacked at run time by its own code. It is not a stock packer. [INFERENCE: from the first 160 bytes and the zlib ratio.]
- `007` and the Empire family keep this program unmodified, and only the 007 loader depacks something at startup.
- Replicants `WAR` and `MREP`: Pack-Ice (`Ice!`). `INTRO.PRG` of `replicants_t2`: Automation v2.3r.
- Copy protection: not seen on `protected`. The title, credits and the "What Is Thy Name Oh Lord" prompt are reached on a plain `.st` image with no key disk, code wheel or manual question up to there. What happens after the name prompt was not reached (below).

## 3. Cleanest base: `disks/protected.st` / `extracted/protected/`

- Its `AUTO/WAR.PRG` is the original program, with no crack hooks, intro or trainer. `007` carries the same bytes under another name (`POWERMON.007`), and the Empire family carries them inside the wrapper, so this is the common root of all the cracks.
- It is a plain file-based layout, easy to patch and diff. Patching `WAR.PRG` needs no rebuilt packer (the program unpacks itself).
- Cons: the boot sector is "Boot 60hz III" (harmless, executable). Nothing else in the disk is changed.
- Replicants uses a different, older Pack-Ice build; avoid it. `replicants_t2` is a good second choice (4-byte diff) when a trainer is wanted.

## 4. Hatari runs (1 MB STE, TOS 1.62, Hatari 2.6.1, `tools/stharness.py` with Xvfb)

Screenshots (git-ignored, in `work/shots/`):

| File | What |
|---|---|
| `prot_floppy_0.png` | blank white screen at 10 s |
| `prot_floppy_3.png` | castle intro picture (about 55 s) |
| `prot_q_2.png`, `prot_hd2_4.png`, `prot_hd2_7.png` | Powermonger title logo with credits ("Special Thanks to", "Designed by Bullfrog") |
| `prot_f2_c1.png`, `prot_n_c.png` | the "What Is Thy Name Oh Lord" prompt (floppy run) |
| `prot_512k_*.png` | 512 KB run: castle picture and title again |
| `empire_hd_0.png`, `empire_hd_6.png` | Empire cracktro from a GEMDOS folder |
| `prot_hd3_*.png` | the HD run after it fails |

### Floppy boot of `protected.st` (works)

Boot flow from the Hatari trace:
1. TOS runs the boot sector (it prints the "Boot 60hz III" text through BIOS).
2. TOS runs `\AUTO\*.PRG`: `Fsfirst("\AUTO\*.PRG")`, `Pexec(0, "\AUTO\WAR.PRG")` (reads the file with `Rwabs`).
3. After `Super` the game makes no more GEMDOS or BIOS calls. [INFERENCE] it talks to the FDC directly (`A:` LED lit, FDC status in the status bar), so game data is read by its own sector loader, not by file name.
4. Sequence: black/white for about 50 s, castle picture, Powermonger logo with "Special Thanks" and "Designed by" credits, then the name prompt. Timing differs by run by tens of seconds.

The name prompt shows the caret, but typing `a b` (Hatari scancodes and xdotool keys) and Return did not accept or visibly echo a name in the tries made; I did not get past it to the map. The first game screen is therefore the name prompt. `[INFERENCE]` the title screens must finish loading before keys count.

### 512 KB

`--memsize 512` also reaches the castle picture and title credits (`prot_512k_*.png`). The map or play screens were not reached, so 512 KB is not proven sufficient. The program's own header sizes (text `$45E90` = 286 KB) fit in 512 KB.

### GEMDOS folder (`--harddrive`)

- Scratch copy of `extracted/protected` as `C:` (`AUTO/WAR.PRG` and `DATA/`), run with `--auto C:\AUTO\WAR.PRG`. TOS 1.62 also runs `C:\AUTO` by itself, so the program started once from the AUTO scan. GEMDOS trace: `Fsfirst("\AUTO\*.PRG")`, `Pexec(0, "\AUTO\WAR.PRG")`, `Super`, and nothing else.
- The castle picture and the title/credits screens appear (`prot_hd2_4.png`), so they are in the program, not on disk. The `A:` LED lights although no disk is inserted.
- Then the game dies: `WARN: Address Error reading at address $10ed, PC=$108c`, followed by `Pterm(-1)` (`prot_hd3_2.png` onwards: black). So the original **does not run from a GEMDOS folder**: its loader needs the floppy in `A:`, because it reads game data by direct FDC access (inferred from the trace; I did not decode the loader).
- To patch for HD, the loader must be found and replaced by GEMDOS file loads. That is the first job of the next phase.
- Empire family (`empire_t_b`, from a GEMDOS folder): the cracktro runs (`empire_hd_0.png`), then waits in `Crawcin` for a key. Hatari did not accept `y`/space injected with xdotool there, so I did not get past the trainer prompt. [INFERENCE] the Empire wrapper does not change the loader (the original program is embedded unchanged), so it also needs the floppy.

## 5. Not done

- No performance analysis, no unpacking of the Replicants `WAR` or of the main program's own stage, no look at what the loader reads.
- The map screen and the actual game were not reached, so manual/protection checks after the name prompt are unknown.
