# Gods (Atari ST) — Adaptive AI & Dynamic Difficulty Investigation

**Question:** Were the Bitmap Brothers telling the truth when they claimed *Gods*' AI adapts when it sees the player struggling or finding the game too easy? What mechanisms actually exist in the 68000 code?  
**Source analyzed:** Live 1 MB RAM dump (`work/ram_level1.bin`) of Level 1 + disk image `originals/GODS/GO2` (Levels 2–4 strings), disassembled and traced with `capstone`.

---

## 1. The Verdict

**Yes — they were telling the truth about adaptive *help/reward* triggers, and they genuinely built unusually sophisticated tactical monster AI for 1991 — but the two systems are completely separate.**

Specifically, *Gods* contains **three distinct mechanisms** (plus one unexpected anti-piracy trap in this Gamex build):

| Claim / Mechanism | Exists in Code? | How It Actually Works |
|---|---|---|
| **Game detects struggling vs. skilled players and adapts rewards** | **YES** (`$019dd0–$01a560`) | A full **rule-based trigger engine** (up to 40 rules per sub-level) explicitly evaluates **Player Health (`$f40.w`)**, **Elapsed Level Time (`$f8c.l`)**, and **Player Score (`$450–$456`)** to spawn `"HELP BONUS"`, `"SPEED BONUS"`, `"HEALTH AND LIVES BONUS"`, `"LIVES BONUS"`, and `"SPECIAL BONUS"` items, shortcuts, or rooms. |
| **Monsters dynamically scale down HP / speed / aggression when you struggle** | **NO** | There are **zero references** in the entire monster AI (`$008da0–$00a950`) to player health, lives, score, or elapsed time. Monsters never "go easier" on a struggling player. |
| **Monsters have smart tactical AI (dodging, flanking, stealing items, pack behavior)** | **YES** (`$008fa6–$00a950`) | Genuinely impressive 1991 AI: a **48-probe 2D spatial hazard/bullet-dodging field**, **6-sector flanking**, **item theft**, and **100-point leader-follower pack trails**. |
| **Progressive / New-Game+ difficulty scaling** | **YES** (`$00402.w` at `$00d85a`) | Static scalar (`0` on Levels 1–3, `1` on Level 4, `2–4` on repeat loops) that reduces player weapon damage against monsters by 25%–75%. |

---

## 2. Mechanism 1: The Adaptive Performance Trigger Engine (`$019dd0–$01a560`)

This is the exact mechanism behind the Bitmap Brothers' famous "the game watches how you play and helps you if you struggle" interviews.

### 2.1 How the Engine Works
Each sub-level loads a table of up to **40 triggers** (`$f60.w`, `$06e21c` in Level 1), each 24 bytes (`$18`) wide:
- **3 AND-ed conditions** (opcode + 16-bit parameter at offsets `+$00/$02`, `+$04/$06`, `+$08/$0a`), evaluated via `$019e78` using the 15-entry jump table at `$01a048`.
- **Target coordinates & action** (`+$0c` X, `+$0e` Y, `+$10` action opcode + bit 15 flag, `+$12` item/wave/param), dispatched at `$019e62` via the 15-entry jump table at `$01a00c`.
- **Ticker message ID** (`+$14`), looked up via `$f64.w` (`$06eb7c`) into the string table at `$e10.w` (`$06f99e`) and scrolled across the bottom status bar via `$17406`.

### 2.2 All 15 Condition Opcodes (`$01a048`)
Disassembled directly from `$01a08c–$01a558`:

| Opcode | Address | Condition Tested |
|---:|---|---|
| **0** | `$01a08c` | Always true (no-op / unused slot) |
| **1** | `$01a3be` | Player **has item `d6`** in one of the 4 inventory slots (`$48a`, `$48c`, `$48e`, `$490`) |
| **2** | `$01a3da` | Player **does not have item `d6`** in inventory |
| **3** | `$01a3f8` | Player **has weapon `d6`** in one of the 3 weapon slots (`$95e`, `$9f0`, `$a82`) |
| **4** | `$01a40e` | Player **does not have weapon `d6`** |
| **5** | `$01a426` | Trigger/event `d6` **has already fired** (`$f68.w` state `< 0`) |
| **6** | `$01a43c` | Trigger/event `d6` **has not fired** |
| **7** | `$01a452` | **Player Health (`$f40.w`) > `d6`** (max health is `$18` = 24) |
| **8** | `$01a45e` | **Player Health (`$f40.w`) < `d6`** |
| **9** | `$01a46a` | **Elapsed Level Time (`$f8c.l / 50` s) > `5 × d6` seconds** (slow / struggling!) |
| **10** | `$01a482` | **Elapsed Level Time (`$f8c.l / 50` s) < `5 × d6` seconds** (fast / skilled!) |
| **11** | `$01a49a` | Lever/switch `d6` is **ON** (`$1d4a4` bit 0 set) |
| **12** | `$01a4b6` | Lever/switch `d6` is **OFF** |
| **13** | `$01a4ea` | **Player Score (`$450–$456`) > `5,000 × d6`** (high score / skilled!) |
| **14** | `$01a522` | **Player Score (`$450–$456`) < `5,000 × d6`** (low score / struggling!) |

### 2.3 Action Opcodes (`$01a00c`)
When all 3 conditions pass, the trigger fires once (marked `$ffff` at `(a0)`), optionally consumes key items (`$19f16`), displays its message, and runs one of 15 actions:
- `ACT[0]` (`$1a2b2`): **Spawn item** `+$12` at `(X, Y)` (e.g., health, extra life, shield, teleport stone, treasure)
- `ACT[1]` (`$1a330`): **Spawn weapon** `+$12` at `(X, Y)`
- `ACT[2]` (`$1a71e`), `ACT[3]` (`$1a25e`), `ACT[4]` (`$1a1de`): Open doors / gates / hidden passages
- `ACT[5]` (`$1a1ce`): Spawn monster wave `+$12`
- `ACT[6]` (`$1a0aa`): Open / reveal nearby chest or container
- `ACT[7]` (`$1aa7c`), `ACT[8]` (`$1aabc`): Open / close trapdoor (modifies map & collision tile)
- `ACT[9]` (`$1a84e`): Modify 3-tile map wall/doorway
- `ACT[10]` (`$1a390`): Remove weapon `+$12`
- `ACT[11]`/`ACT[12]` (`$1a094`/`$1a0a0`): Enable / disable PAL1 Timer B sky gradient (`$3da.w`)
- `ACT[14]` (`$1a08e`): Reset elapsed level timer (`clr.l $f8c.w`)

### 2.4 Concrete Verified Examples in Level 1 (`$06e21c`)
From the live Level 1 trigger table and message table (`$06eb7c`):
- **Struggling player → `"HELP BONUS"` (Trigger `[28]`):**
  - `c1 = COND[14](24)` (**Score < 120,000**) AND `c2 = COND[9](24)` (**Elapsed Time > 120 seconds**)
  - Action: `ACT[0]` spawns **`item[54]` (`"teleport stone"`)** at `(1658, 839)` and prints **`"HELP BONUS"`**!
- **Fast/skilled player → `"SPEED BONUS"` (Trigger `[6]`):**
  - `c1 = COND[10](12)` (**Elapsed Time < 60 seconds**)
  - Action: `ACT[0]` spawns **`item[5]` (`"bag of gold"`)** at `(297, 688)` and prints **`"SPEED BONUS"`**!
- **Other Level 1 & Levels 2–4 triggers:**
  - Level 1's message table also contains `"health  and lives bonus"`, `"lives bonus"`, `"health, lives and score bonus"`, `"special bonus"`, `"treasure room"`, and `"short cut"`.
  - Scanning `originals/GODS/GO2` confirms `"help bonus"`, `"lives help"`, `"speed and special"`, and `"on target for huge ..."` triggers across Levels 2, 3, and 4 using the exact same engine.

**Key takeaway:** This is **authored, rule-based adaptive scripting**, not a continuous statistical AI. Because the level designers placed `"help bonus"` triggers gated on low health (`COND[8]`), slow time (`COND[9]`), and low score (`COND[14]`) — and `"speed bonus"` / `"health and lives bonus"` triggers gated on high health (`COND[7]`), fast time (`COND[10]`), and high score (`COND[13]`) — the game genuinely reacts to how well or poorly you are doing!

---

## 3. Mechanism 2: The Monster AI Engine (`$008da0–$00a950`)

We audited every single reference in the entire binary (`$001000–$021000`) to player health (`$f40.w`), player lives (`$394.w`), score (`$450.w`), and elapsed time (`$f8c.w`). **None of them are ever read by the monster spawners or monster AI.**

However, the **tactical monster AI** itself is remarkably sophisticated for a 1991 8 MHz 68000 platformer:

1. **2D Spatial Hazard & Bullet-Dodging Field (`$0094c8 → $00952a`):**
   - Every frame, `$005fe2` clears and `$016f94` populates a screen-space 8×8-pixel collision/hazard grid at `($526.w)` (48 bytes/row) marking solid terrain and active player projectiles.
   - Any monster wave with evasion byte `$f(a4) > 0` runs `$00952a`, which samples up to **48 radial probe offsets** (`$b34e`) around the monster with stride `(16 - evasion) & 15` (higher evasion = denser scan). Whenever a probe hits an obstacle or projectile, it accumulates a repulsion vector from `$b3ae`, steering the monster away from incoming fire and around walls!
2. **5-Mode Behavioral State Machine (`$0096f8`, jump table `$009792`):**
   - Each wave definition (`a4`) specifies **two behavior modes** (low and high nibbles of `$8(a4)`) plus a probabilistic switch weight (`$9(a4)`):
   - **Mode 0 (`$0097a6`):** Direct pursuit of the player's coordinates (`$35e.w`, `$360.w`).
   - **Mode 1 (`$009ada` + `$009d9a`):** **6-Sector Spatial Flanking / Positioning.** Every frame, `$009d9a` tests the player's bounding box against 6 screen regions (`$9e1a`) and scores them into `$75e.w`. Monsters in Mode 1 pick the highest-scoring (or adjacent) sector and choose a randomized target point inside it — causing enemies to flank, hold high ground, or keep distance rather than blindly walking into the player.
   - **Mode 2 (`$00997a` ground, `$00a178` flying):** **Item Theft.** Scans up to 20 on-screen pickups (`$14c6.w`). If the monster isn't already carrying an item (`$10(a5) < 0`) and its flags allow stealing that item class, it targets and grabs the item, carries it visibly on screen (`$90b8`/`$a06a`), switches to its secondary mode (typically Mode 1 flee/flank), and either keeps it until killed or drops it with a `1/128` per-frame chance (`$a0be`).
   - **Mode 3 (`$009c66`):** Formation / orbit phase counter (`$1aa(a6)`).
   - **Mode 4 (`$0097f8`):** **Pack Leader-Follower Trails.** When a wave uses pack cohesion (`$a(a4) > 0`), the pack leader (`$19(a5) == 1`) records its `(x, y)` position every frame into a **100-entry ring buffer** (`$18(a6)–$1a7(a6)` at `$008fe6–$009020`). Pack followers read staggered historical offsets from this ring buffer, producing organic coordinated pack movement!
3. **Flying / Wall-Crawling State Machine (`$00a018`, jump table `$009e64`):**
   - 8 states (`$a40c–$a87e`) handling wall/ceiling adherence, swooping, turning at ledges, projectile firing (`$009676`, shared with ground monsters), and item theft (`$00a178`).

---

## 4. Mechanism 3: Static Progression / New-Game+ Difficulty (`$00402.w`)

A single global difficulty scalar `$0402.w` scales enemy toughness across late-game and repeat playthroughs:
- `0` on Levels 1–3.
- Set to `1` on Level 4 (`$00fece: cmpi.w #$4, $352.w → move.w #$1, $402.w`).
- Incremented on beating the Level 4 Guardian (`$00c0d6`) and on game loop restart (`$0034a6`, clamped to `2..4`).
- In the monster-hit routine (`$00d85a`), when `$0402.w > 0`, it refunds `damage >> (3 - $402.w)` back to the monster's HP — effectively reducing player weapon damage by 25% (Level 4), 50% (Loop 2), or 75% (Loop 3+).

---

## 5. Bonus Discovery: 4 Live Rob Northen Copylock Traps in the Gamex Build

While tracing the monster spawners (`$008da0` and `$009ea8`), we uncovered an extraordinary bug in the Gamex HD conversion (`originals/GODS/`):

```m68k
008da4: tst.l  $fec8.l          ; reads immediate operand of `move.l #$873b4953, $400.w` at $fec6!
008daa: beq.b  $8dc2            ; only skips if Copylock subtracted $873b4953 -> 0!
008dac: move.b #$a, $b(a4)      ; OVERWRITES monster max_speed = 10
008db2: move.b #$a, $c(a4)      ; OVERWRITES monster accel = 10
008db8: clr.b  $8(a4)           ; OVERWRITES monster behavior = 0 (pure chase!)
008dbc: move.b #$f, $f(a4)      ; OVERWRITES monster evasion = 15 (max bullet dodging!)
```

In `work/ram_level1.bin`, the magic Rob Northen Copylock key **`$873b4953`** is still un-decrypted at **all four** anti-piracy trap sites:
1. **`$00fec8` (`$873b4953`, should be `$00000000`):** Causes both the Ground (`$008da4`) and Flying (`$009eac`) monster spawners to overwrite every wave's speed, acceleration, behavior, and evasion to max-aggression pure-chase — **ironically erasing the nuanced per-wave AI in this Gamex crack!**
2. **`$00d864` (`$873b4953`, should be `$00000000`):** Forces player weapon damage `d3 = 1` when `$402.w > 0` (Level 4 / NG+).
3. **`$010ffe` (`$873b4953`, should be `$00000000`):** Causes **Power Potions** (`"increases weapon power"`) to skip `addq.w #$1, $3a2.w`, breaking weapon upgrades!
4. **`$00b4ee` (`$873b4f2f`, should be `$000005dc` = 1,500):** Gives the Level Guardian boss `$073b4f2f` (~121 million) HP instead of 1,500 HP!

Fixing these four longwords will be essential before doing any gameplay testing or STE enhancement work on this Gamex base.
