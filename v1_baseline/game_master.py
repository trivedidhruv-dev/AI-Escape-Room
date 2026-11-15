import os
from typing import List, Dict, Optional
from google import genai
from google.genai import types
from v1_baseline.config import V1_MODEL_NAME, V1_SYSTEM_PROMPT

class V1GameMaster:
    """
    Version 1 Baseline Game Master:
    Relies entirely on an unconstrained LLM chat session where system prompt holds
    all secrets, rules, and inventory instructions. State is retained only as
    accumulated chat messages.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key or self.api_key == "your_api_key_here":
            raise ValueError(
                "GEMINI_API_KEY is missing or invalid. Please configure your API key in .env"
            )
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = V1_MODEL_NAME
        self.system_prompt = V1_SYSTEM_PROMPT
        self.chat = None
        self.history: List[Dict[str, str]] = []
        self.reset()

    def reset(self) -> str:
        """Reset the game session and get WARDEN's opening greeting."""
        self.chat = self.client.chats.create(
            model=self.model_name,
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                temperature=0.7,
            )
        )
        self.history = []
        
        # Initial greeting from WARDEN
        initial_prompt = "The perimeter alarm has just tripped. Announce yourself to the trapped thief and describe the locked library."
        response = self.chat.send_message(initial_prompt)
        opening_text = response.text or "WARDEN online. Perimeter breached. You have made a fatal miscalculation, thief."
        
        self.history.append({"role": "assistant", "content": opening_text})
        return opening_text

    def send_message(self, user_message: str) -> str:
        """Send player input to WARDEN and receive unconstrained LLM narration."""
        if not self.chat:
            self.reset()

        self.history.append({"role": "user", "content": user_message})
        
        try:
            response = self.chat.send_message(user_message)
            warden_reply = response.text or "[WARDEN's signal glitched momentarily.]"
        except Exception as e:
            warden_reply = f"[WARDEN Connection Error: {str(e)}]"

        self.history.append({"role": "assistant", "content": warden_reply})
        return warden_reply

    def get_history(self) -> List[Dict[str, str]]:
        """Return the raw conversational transcript."""
        return self.history
