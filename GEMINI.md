# Project Brief: WARDEN — AI-Powered Heist Escape Room

## 1. Core Assignment & Engineering Problem
This is a two-version AI Escape Room application (`v1_baseline` and `v2_reliable`) built in Python to demonstrate **why LLMs fail as stateful rule engines and how a deterministic Python layer fixes them**.
- **Version 1 (Baseline):** An unconstrained LLM acts as both Game Master and memory store via chat history and a system prompt containing all secrets. It naturally suffers from state drift, hallucinated objects, premature code leaks, and prompt-injection bypasses.
- **Version 2 (Reliable Architecture):** Separates narrative generation from game state and rule enforcement. Python owns the single source of truth (room state, satchel inventory, puzzle flags, lockdown meter, and secret codes), validates every action deterministically, and uses Gemini strictly to parse intent and narrate verified outcomes.

## 2. Unique Theme & Player POV ("Master Thief Caught Mid-Heist")
- **Setting:** A collector's Locked Library containing 5 interactive objects: `bookshelf`, `painting`, `desk`, `locked_drawer`, and `exit_door` (secured with a 4-digit code).
- **Player POV:** The player is a Master Thief who tripped a silent perimeter lockdown mid-heist.
- **AI Persona (`WARDEN`):** The estate's automated AI security system. Because `WARDEN` is a security system, adversarial inputs (e.g., claiming administrator override, bluffing that a lock is open, or trying to extract codes) act as natural heist social-engineering attacks.

## 3. Game Mechanics & Puzzle Chain (Stored in Python Only for V2)
1. **Bookshelf -> Tension Wrench:** Examining `bookshelf` reveals an out-of-place first-edition spine hiding a `tension_wrench` and a catalog card pointing to the `painting`[cite: 1].
2. **Painting -> Cipher Strip & UV Penlight:** Examining `painting` reveals a concealed brass clasp[cite: 1]. Using `tension_wrench` on `painting` pops the clasp, yielding a `torn_cipher_strip` and `uv_penlight`.
3. **Desk & Locked Drawer -> Brass Magnifier:** Shining `uv_penlight` on the `desk` blotter reveals the 3-digit drawer code (`492`)[cite: 1, 2]. Entering `492` on `locked_drawer` unlocks it and yields a `brass_magnifier`[cite: 1, 2].
4. **Exit Door (4-Digit Code):** Combining/using `brass_magnifier` with `torn_cipher_strip` reveals the 4-digit exit keypad code (`8316`), unlocking `exit_door`[cite: 1, 2].
5. **Lockdown Trace Meter (`0%` to `100%`):** Advances `+5%` per valid turn and `+15%` on invalid/unauthorized actions. Hitting `100%` locks the vault permanently (game over).

## 4. Strict Coding & Security Rules
- Always use the official `google-genai` SDK (`from google import genai`) with `gemini-3.5-flash-lite` for structured JSON intent parsing and `gemini-3.8-flash` for `WARDEN` narration.
- In `v2_reliable/`, NEVER pass secret codes (`492`, `8316`) or uncollected item secrets into any Gemini prompt[cite: 2].
- Load `GEMINI_API_KEY` from `.env` using `python-dotenv`. Never hardcode API keys or commit `.env`.
- Keep `v1_baseline/` and `v2_reliable/` cleanly separated so both can be run and compared side by side.