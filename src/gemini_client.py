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


_PROMPT = """You are analyzing a photo of a math problem that a student may have answered incorrectly.

Format any math expression as LaTeX, using $...$ for inline math and $$...$$ for display blocks. Plain prose stays as plain text. Do not use Unicode math symbols or control characters; write everything in standard LaTeX (e.g. \\sqrt, \\frac, \\binom, \\cdot, \\times).

Return a JSON object with these fields:
- problem: the full text of the math problem, transcribed exactly, with math wrapped in $...$ (e.g. "Solve $x^2 + 3x = 10$.").
- student_answer: the student's written answer (which is wrong), with math in LaTeX wrapped in $...$ or $$...$$. If you cannot find one, return an empty string.
- category: classify the problem into EXACTLY ONE of these categories: {categories}. Return the category string verbatim.
- ideal_answer: the correct final answer, with math in LaTeX wrapped in $...$ or $$...$$.
- explanation: a short, kid-friendly step-by-step explanation. Plain prose for the words; wrap every math expression in $...$ or $$...$$. Separate steps with real newline characters in the JSON string (the JSON encoder will emit them as \\n on the wire). Do NOT write the two-character sequence backslash-n as visible text, and do NOT use <br> or other HTML tags.
"""


def _normalize_newlines(s: str) -> str:
    # Defensive fix for models that emit the literal two-character sequence "\n"
    # instead of an actual newline. Safe because LaTeX has no \n command.
    return s.replace("\\n", "\n").replace("\\r", "")


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
    print("Start Analyzing image with Gemini...")
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
    print("Finished analyzing image with Gemini.")
    result = MistakeAnalysis.model_validate_json(response.text)
    result.problem = _normalize_newlines(result.problem)
    result.student_answer = _normalize_newlines(result.student_answer)
    result.ideal_answer = _normalize_newlines(result.ideal_answer)
    result.explanation = _normalize_newlines(result.explanation)
    return result
