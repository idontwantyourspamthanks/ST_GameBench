; Powermonger WW1 (Cobra #26): base-independent patch carrier.
;
; PROBLEM: WW1.PRG's text has NO relocation table (28 + 61622 == the file length), so the
; text cannot be patched by absolute address and a data segment cannot be appended after it
; (TOS reads the reloc table from there). The ATOMIK stub, however, is PLAINTEXT and its
; first instructions run with a7 pointing at a7 -> the caller's return address, and the
; stub itself is at the program base. So the entry (`text $0`) can be replaced by a
; base-relative stub: everything below computes addresses from its own PC.
;
; This is the *only* text patch: `text $0..$5` (6 bytes: `3f 3c 00 02 4e 4e 20 40` -> a
; `bra` into... no: a bra cannot reach the data segment, which is not loaded).
;
; So there is no data segment. Everything the patch needs must be inside the existing bss
; (92679 bytes, always cleared) or in free RAM. Consequence:
;   * the carrier code itself must live in the text (we have the 6-byte entry, too small),
;   * or be loaded from a file by the carrier.
;
; DECISION: load a companion file. `WW1PATCH.BIN` sits next to WW1.PRG; the 6-byte entry
; stub calls TOS Fopen/Fread via a small routine that must also fit in 6 bytes - impossible.
;
; FINAL DESIGN (what this file implements): patch the *depacked image*, not the file.
; A tiny external loader (`BOOT.PRG`) runs first (AUTO folder), reads WW1.PRG, depacks it
; with the ATOMIK routine in Python at build time (tools/atomik.py), applies the patch
; sites to the unpacked image, re-packs nothing, and writes a NEW plain PRG
; (`WW1P.PRG`) with text = the patched image and no depacker. That is a pure file-level
; build with no runtime carrier at all.
;
; For that, tools/atomik.py must work. It is the remaining piece.
	org	$0
	nop
