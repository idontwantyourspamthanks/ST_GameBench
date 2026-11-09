# TOS images (not included)

Put your own TOS ROM images here. The tools expect these names:

| File | Use | MD5 of the images used for testing |
|---|---|---|
| `TOS_1_02.img` | ST | `b2a8570de2e850c5acf81cb80512d9f6` |
| `TOS_1_04.img` | ST / Mega ST | `036c5ae4f885cbf62c9bed651c6c58a8` |
| `TOS_1_06.img` | STE (only) | `6033f2b9364edfed321c6931a8181fd2` |
| `TOS_1_62.img` | STE (only), the default | `1cbc4f55295e469fc8cd72b7efdea1da` |
| `TOS_2_06.img` | Mega STE | `c9093f27159e7d13ac0d1501a95e53d4` |
| `TOS_3_05_us.img` | TT | `19cd81e1c3049bf408ad426dc5c3b2e0` |
| `TOS_3_06_uk.img` | TT | `dd1010ec566efbd71047d6c4919feba5` |
| `TOS_4_00.img` | Falcon (this dump is 1 byte short but boots) | `ed2647936ce4bd283c4d7dfd7ae09d1c` |
| `TOS_4_01.img` | Falcon | `b338bacb2fc453bab61bcc1e2cf5076b` |
| `TOS_4_02.img` | Falcon | `9e880168d0a004f7f5e852be758f39e4` |
| `TOS_4_04.img` | Falcon | `e5ea0f216fb446f1c4a4f476bc5f03d4` |
| `EmuTOS_1024k.img` | TT / Falcon (free, GPL; from the EmuTOS project) | `f187a26efd62d040b93e468a21b67b61` |

`play.sh` and the harnesses (`stharness.TOS['3.06']`, `TOS['4.04']`, ...) use the TT/Falcon images when present, else EmuTOS.
`MultiTos - Hard Disk Version.MSA` (optional) is a MultiTOS install floppy, not a ROM.
