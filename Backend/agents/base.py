from abc import ABC, abstractmethod
import os
from google import genai

class SubAgent(ABC):
    def generate(self, instruction: str, request: str) -> str:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=f"{instruction}\n\nUser request:\n{request}",
        )
        return response.text or "The model returned an empty response. Please try again."

    @abstractmethod
    def run(self, request: str) -> str:
        pass

    @property
    @abstractmethod
    def cost(self) -> int:
        pass
