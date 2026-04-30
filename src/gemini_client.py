import os

from google import genai
from google.genai import types
from pydantic import BaseModel

from config import CATEGORIES


class MistakeAnalysis(BaseModel):
    problem: str
    student_answer: str
    category: str
    ideal_answer: str
    explanation: str


_PROMPT = """You are analyzing a photo of a math problem that a student has answered incorrectly.

Return a JSON object with these fields:
- problem: the full text of the math problem, transcribed exactly. Use plain text; for math expressions, write them inline (e.g. "x^2 + 3x = 10").
- student_answer: the student's written answer (which is wrong). If you cannot find one, return an empty string.
- category: classify the problem into EXACTLY ONE of these categories: {categories}. Return the category string verbatim.
- ideal_answer: the correct final answer.
- explanation: a short, kid-friendly step-by-step explanation of how to solve it correctly. Use plain text with line breaks between steps.
"""


_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.")
        _client = genai.Client(api_key=api_key)
    return _client


def analyze_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> MistakeAnalysis:
    client = _get_client()
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    prompt = _PROMPT.format(categories=", ".join(CATEGORIES))
    response = client.models.generate_content(
        model=model,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            prompt,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=MistakeAnalysis,
        ),
    )
    return MistakeAnalysis.model_validate_json(response.text)
