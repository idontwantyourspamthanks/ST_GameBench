---
name: game-delegation
description: How to delegate Atari ST game reverse-engineering and patching work in gamebench to subagents so the results are trustworthy. Covers model routing, the evidence contract, task template, blob-range and emulator-concurrency allocation, provider-failure handling, and the verification the lead must re-run. Use before spawning any task/smol/tiny agent in this project.
---

# Delegating game work to subagents

## Model routing (user's standing instruction)
- **`task` (Sonnet) or the lead (Opus):** anything that drives the emulator or the game UI.
  - This covers navigation, scripted input, judging screenshots, multi-step dynamic debugging, and running gates.
  - Small models second-guess themselves when the UI misbehaves.
- **`smol` (Qwen) and `tiny` (DeepSeek Flash):** pure code tasks only.
  - Examples: a 68000 routine written against an exact register/memory contract, Python tooling, table generators, static disassembly reading.
  - Their output counts only after the lead or a Sonnet agent has run a gate on it in the emulator.
- **Escalate on a stall:** if an agent spends more than about 30 minutes on one bug without new evidence, stop it. Then fix it yourself or hand it to a stronger model with a precise handoff.
  - Example: the jsr/jmp load-hook crash took the lead about 5 minutes after Qwen had spent 40 on it.

## Task template
Put the shared facts in `context`. Each task needs a target, the change, and acceptance tests.
- **Read first:** PLAN.md, patches/README.md, work/baseline.md, and the specific `work/notes/*.md`. Also point at the skills: `st-hatari-harness`, `pp-haga-conversions`, `st-game-speedup`, plus the game's own skill or notes.
- **Exact inputs:** addresses, snapshot names, commands. Never "find the renderer".
- **Allocations:**
  - A blob address range per agent, checked against `mw2patch.py build` and the map in `mw2-patching`.
  - Distinct patch-file prefixes.
  - Distinct `--out` build dirs.
- **Concurrency cap:** at most 2–3 Hatari instances per agent, and a lower total if several agents run emulators.
- **Rules to state in every task:**
  - "Do NOT spawn subagents." Nested agents died on provider errors and took the parent down with them.
  - Don't modify game files, `tools/*`, other agents' patches, or PLAN.md.
  - Write only your own note and patch files.
- **Evidence contract (verbatim):** every claim cites a disassembly line (address plus text) or raw tool output the agent produced; anything unproven is marked `[INFERENCE]`; paste the raw gate outputs into the final report.
- **Acceptance:** numbered tests with observable outputs (abtest exit code, fps numbers, group-end equality tables, cold-boot `MWPO` plus a screenshot).

## Shared tools: single owner
- `tools/*`, `patches/README.md`, PLAN.md and `work/baseline.md` belong to the lead.
- If an agent hits a tool limit (site-table size, payload size, harness bug), it messages the lead: `write agent://<lead>`. The lead changes the tool, and the agent works from a private copy meanwhile.

## Verifying returned work (the lead, always)
- Re-run at least one acceptance command yourself, e.g. `abtest`, a cold boot of the default build, or a live mouse/joystick check.
- Spot-check one key static claim with `m68dis` before building on it.
- Known failure modes from this project:
  - **Claims that are wrong but plausible.** "Joystick steering is dead code" was disproved by a 2-minute live test. A patch at `$1b9c0` had the right bytes but no visible effect, because the colour seed was elsewhere.
  - **Status lines that overstate.** "Validated" turned out to be half true. Insist on pasted tables.
  - **Harness or emulator flakiness reported as game bugs.** Black screens came from the fade or a missed click. Crashes came from a shared Xvfb. Re-run before believing them.
  - **Provider errors** (`failed to evaluate membership entitlement`). Check what the agent left on disk (notes, scratch patches) and relaunch with a summary of its progress. Don't redo the work.
