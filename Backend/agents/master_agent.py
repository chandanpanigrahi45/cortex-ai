import os
from dotenv import load_dotenv
import re
from google import genai
from agents.sub_agents import CodeAgent, PDFAgent, PPTAgent, ImageAgent, VideoAgent, ChatAgent

# Load environment variables from .env file
load_dotenv()

# Map destination to agent instances
AGENT_MAP = {
    "code": CodeAgent(),
    "pdf": PDFAgent(),
    "ppt": PPTAgent(),
    "image": ImageAgent(),
    "video": VideoAgent(),
    "chat": ChatAgent()
}

def get_agent_instance(destination: str):
    return AGENT_MAP.get(destination, AGENT_MAP["chat"])

def get_master_agent():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")

    client = genai.Client(api_key=api_key)
    
    prompt = """You are the Master Router of Cortex AI. Analyze the user's request and determine the best agent to handle it.

User Request: {request}

Rules for routing:
- 'code': if the request asks for programming, bug fixing, or scripts.
- 'pdf': if the request involves reading, summarizing, or analyzing documents.
- 'ppt': if the request asks to create a presentation or slides.
- 'image': if the request asks to generate or edit a picture.
- 'video': if the request asks to create or edit a video.
- 'chat': for any general conversation, advice, or math that doesn't fit above.

Return ONLY the agent name: code, pdf, ppt, image, video, or chat"""
    
    def route(request: str) -> str:
        response = client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=prompt.format(request=request),
        )
        text = (response.text or "").lower().strip()
        match = re.search(r"\b(code|pdf|ppt|image|video|chat)\b", text)
        return match.group(1) if match else "chat"

    return route

if __name__ == "__main__":
    print("Cortex AI Master Router Booting Up...")
    router_chain = get_master_agent()
    
    test_prompts = [
        "Write a Python script for web scraping",
        "Create a presentation on Global Warming",
        "Generate a 4k image of a futuristic city",
        "Summarize this PDF document"
    ]
    
    for req in test_prompts:
        result = router_chain(req)
        print(f"Request: '{req}' -> Routed to: [{result.upper()} AGENT]\n")