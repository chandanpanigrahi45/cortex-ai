from agents.base import SubAgent

class CodeAgent(SubAgent):
    def run(self, request: str) -> str:
        return self.generate(
            "Act as a senior software engineer. Solve the programming task, explain important assumptions, and include tests when useful.",
            request,
        )
    @property
    def cost(self) -> int:
        return 5

class PDFAgent(SubAgent):
    def run(self, request: str) -> str:
        return self.generate(
            "Act as a document analyst. Analyze only the text or document details supplied by the user; do not claim to have read an attachment that is not present.",
            request,
        )
    @property
    def cost(self) -> int:
        return 2

class PPTAgent(SubAgent):
    def run(self, request: str) -> str:
        return self.generate(
            "Create a clear presentation plan with a title, ordered slide headings, concise slide content, and visual suggestions.",
            request,
        )
    @property
    def cost(self) -> int:
        return 3

class ImageAgent(SubAgent):
    def run(self, request: str) -> str:
        return self.generate(
            "Create a detailed image-generation prompt matching the user's request. Do not claim that an image file was generated.",
            request,
        )
    @property
    def cost(self) -> int:
        return 5

class VideoAgent(SubAgent):
    def run(self, request: str) -> str:
        return self.generate(
            "Create a video concept with a concise storyboard, scene descriptions, and a production-ready generation prompt. Do not claim that a video file was generated.",
            request,
        )
    @property
    def cost(self) -> int:
        return 10

class ChatAgent(SubAgent):
    def run(self, request: str) -> str:
        return self.generate("You are a helpful, accurate general-purpose assistant.", request)
    @property
    def cost(self) -> int:
        return 1
