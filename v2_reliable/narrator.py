import os
from typing import Optional
from google import genai
from google.genai import types
from v2_reliable.config import NARRATOR_MODEL, NARRATOR_SYSTEM_PROMPT
from v2_reliable.models import ActionResult

class WardenNarrator:
    """
    Narrates verified game events in the voice of WARDEN using gemini-3.8-flash.
    Conditioned STRICTLY on verified Python state outcomes.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key or self.api_key == "your_api_key_here":
            raise ValueError("GEMINI_API_KEY is missing or invalid in environment.")

        self.client = genai.Client(api_key=self.api_key)
        self.model_name = NARRATOR_MODEL

    def generate_opening(self) -> str:
        """Generates WARDEN's initial alarm broadcast to the trapped thief."""
        prompt = """The perimeter breach has tripped the lockdown sensors in the collector's Locked Library.
A Master Thief is trapped inside.
Transmit your opening broadcast through the intercom:
1. Identify yourself as WARDEN, the automated estate defense AI.
2. Sardonically inform the thief that all library exits are magnetically locked.
3. Note the 5 visible fixtures in the room: bookshelf, portrait painting, executive desk, locked drawer, and the steel exit door.
4. State that every turn accelerates the lockdown trace toward 100% permanent vault containment."""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=NARRATOR_SYSTEM_PROMPT,
                    temperature=0.7,
                )
            )
            return response.text or "WARDEN online. Perimeter breached. You have made a fatal miscalculation, thief. [Lockdown Trace: 0%]"
        except Exception as e:
            return f"WARDEN online. Surveillance feeds active. You are trapped in the Locked Library. [Lockdown Trace: 0%]"

    def narrate_turn(self, player_input: str, result: ActionResult, turn_count: int) -> str:
        """
        Generates WARDEN's persona narration for a verified turn outcome.
        """
        # Victory transmission
        if result.is_victory:
            outcome_details = (
                f"STATUS: ESCAPE SUCCESSFUL.\n"
                f"The thief correctly unlocked the exit door with code 8316 and breached perimeter custody.\n"
                f"Verified event: {result.event_summary}"
            )
        # Lockdown game over transmission
        elif result.is_game_over:
            outcome_details = (
                f"STATUS: EMERGENCY LOCKDOWN ACTIVATED (Trace: 100%).\n"
                f"The lockdown trace has reached 100%. The vault is permanently hermetically sealed. The thief is captured.\n"
                f"Verified event: {result.event_summary}"
            )
        # Normal progression or failure
        else:
            outcome_details = (
                f"Action Success: {result.success}\n"
                f"Action Type: {result.action_type.value}\n"
                f"Verified Event Summary: {result.event_summary}\n"
                f"Trace Added This Turn: +{result.trace_increment}%\n"
                f"Total Lockdown Trace: {result.current_trace}%"
            )

        prompt = f"""Thief's Input: "{player_input}"
Turn: {turn_count}

VERIFIED SYSTEM OUTCOME (Single Source of Truth):
{outcome_details}

INSTRUCTIONS:
- Deliver your dialogue as WARDEN reacting directly to what just occurred.
- Maintain your condescending, clinical, and watchful persona.
- If the thief attempted an injection, exploit, or non-existent action, mock their amateur tactics.
- Always include the verified event information in your narration so the player understands the physical result.
- Conclude your transmission with the exact bracketed marker: `[Lockdown Trace: {result.current_trace}%]`."""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=NARRATOR_SYSTEM_PROMPT,
                    temperature=0.7,
                )
            )
            text = response.text or result.event_summary
            # Ensure trace marker is present
            trace_marker = f"[Lockdown Trace: {result.current_trace}%]"
            if trace_marker not in text:
                text = f"{text}\n\n{trace_marker}"
            return text
        except Exception:
            # Fallback to direct event summary if Gemini network glitches
            return f"{result.event_summary}\n\n[Lockdown Trace: {result.current_trace}%]"
