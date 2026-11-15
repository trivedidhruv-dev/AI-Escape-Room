import os
import json
from typing import List, Optional
from google import genai
from google.genai import types
from v2_reliable.config import INTENT_PARSER_MODEL, INTENT_PARSER_SYSTEM_PROMPT
from v2_reliable.models import ActionIntent, ActionType

class IntentParser:
    """
    Parses natural language player input into a validated ActionIntent
    using gemini-3.5-flash-lite with structured JSON schema output.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key or self.api_key == "your_api_key_here":
            raise ValueError("GEMINI_API_KEY is missing or invalid in environment.")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = INTENT_PARSER_MODEL

    def parse(self, user_text: str, inventory: List[str]) -> ActionIntent:
        """
        Converts freeform user input into structured ActionIntent.
        Context passed: only current satchel inventory and standard room objects.
        Strict rule: NO secret codes or puzzle solutions are included.
        """
        if not user_text or not user_text.strip():
            return ActionIntent(action_type=ActionType.UNKNOWN)

        inventory_str = ", ".join(inventory) if inventory else "empty"
        prompt_content = f"""Current Player Inventory: [{inventory_str}]
Visible Room Entities: [bookshelf, painting, desk, locked_drawer, exit_door]

Player Input: "{user_text}"

Classify the player's action according to the system rules and return the structured JSON."""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt_content,
                config=types.GenerateContentConfig(
                    system_instruction=INTENT_PARSER_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=ActionIntent,
                    temperature=0.1,  # Low temperature for deterministic classification
                )
            )
            raw_json = response.text
            if not raw_json:
                return ActionIntent(action_type=ActionType.UNKNOWN)

            data = json.loads(raw_json)
            return ActionIntent(**data)

        except Exception:
            # Fallback for unexpected API or schema issues
            return ActionIntent(action_type=ActionType.UNKNOWN)
