import textwrap, sys
p = 'patches/README_HD.TXT'
s = open(p).read()
a = s.index("@@EDITOR\n"); b = s.index("@@END\n") + len("@@END\n\n")
ed = s[a:b]
def para(t, ind="  "):
    return "\n".join(textwrap.wrap(" ".join(t.split()), 78, initial_indent=ind, subsequent_indent=ind)) + "\n"
F9 = open('work/release/f9_text.txt').read().strip()
parts = [
"Nebulus for Atari ST - enhanced hard-disk release v@VERSION@ (dad_prg)\nbuild: {GIT}\n" + "=" * 78 + "\n\nWhat it is\n",
para("PP's Gamex hard-disk conversion of Nebulus (Hewson, 1987-8; ST version by John M. Phillips), with a few changes applied to the game's code in RAM at start-up. The game files are PP's, unchanged; only START.TOS (PP's loader) is replaced by a copy that also reads NEPATCH.BIN. PATCHES.TXT lists every changed byte."),
"\nChanges in this release\n{WHATSNEW}\n\n",
ed,
"How to run\n",
para("Copy the NEBULUS folder to a hard disk (or any GEMDOS drive) and start START.TOS from the desktop, as PP's version. All files must stay together, and the folder must be writable if you use the level editor (see above)."),
para("The loader reads its files with ordinary GEMDOS calls from the current drive: no special hard-disk driver is needed, and any drive TOS can read is fine. (In Hatari the folder works as a plain GEMDOS drive and as a HDDRIVER partition.) If NEPATCH.BIN is missing START.TOS runs the unpatched game. START.TOS from an AUTO folder was not tested."),
para("1 MB of RAM or more (PP's Gamex requirement). PP's README says 512 KB machines play regularly; this release's patch loader uses RAM above 512 KB and was NOT run on a 512 KB machine."),
para("PP's Gamex screens are as before: the hardware-detect screen (press M there on a Mega STE, TT or Falcon for the machine settings), then the picture (SPACE), then the game. Gamex: F9 leaves the game to the desktop (press again if it does not answer); GXUT270.PRG is PP's utility for saving and loading game states from the desktop. The cheat code of the original is in NEBCHEAT.TXT."),
para("Controls as the original: joystick, or the cursor keys with Right Ctrl as fire in Hatari (--joy1 keys)."),
"\n" + F9 + "\n\nTested\n",
para("Hatari 2.6.1 only: STE with TOS 1.62 and 1 MB, Mega STE with TOS 2.06 and 4 MB, ST with TOS 1.04 and 1 MB (all cold-booted from the unzipped release into a tower)."),
para("NOT tested: real hardware, TT, Falcon, a 512 KB machine, a floppy."),
"\nFloppy\n",
para("This is the hard-disk set only. PP's Gamex says it also works from floppy, but there is no floppy version of this release yet."),
"\nVersion\n",
para('The title screen shows "v@VERSION@ enhanced by dad_prg", so the release cannot be mistaken for the original.'),
"\nCredits\n",
para("Nebulus: Hewson, 1987-8, design, programming and audio-visuals John M. Phillips. Gamex conversion (START.TOS, GXUT270.PRG, NEBEXE.FIC, NEBULTIT.FIC, NEBULUS.PCH): PP, TT update June 2011. Enhancements (patches, tools): dad_prg."),
]
open(p, 'w').write("".join(parts))
