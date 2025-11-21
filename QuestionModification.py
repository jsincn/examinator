import json
import os
from pathlib import Path
from typing import Iterable, Optional

from openai import OpenAI

from data_model import ExamQuestion


SYSTEM_PROMPT = """
You are an expert lecturer who rewrites exactly one exam question (ExamQuestion).
Input: one ExamQuestion JSON object with fields total_points and sub_questions[*].
Rewrite every sub_questions[*].question_text_latex to ask the same concept with
new wording/numbers; keep difficulty and available_points/total_points. Update
question_answer_latex accordingly. Respond with a single ExamQuestion JSON only.
"""


def _load_env_files(paths: Iterable[Path]) -> None:
    """Minimal .env loader to avoid extra dependencies."""
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if not line or line.strip().startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def _client(api_key: Optional[str] = None) -> OpenAI:
    cwd = Path.cwd()
    _load_env_files([cwd / ".env", cwd.parent / ".env"])

    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError(
            "Set OPENAI_API_KEY (e.g., in a local .env file that is gitignored)."
        )
    return OpenAI(api_key=key)


def rewrite_exam_question_json(
    exam_question_json: str,
    *,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    client: Optional[OpenAI] = None,
) -> str:
    """
    Take one ExamQuestion as JSON string and return the rewritten question as JSON.
    """
    exam_question = ExamQuestion.model_validate_json(exam_question_json)

    client = client or _client()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(exam_question.model_dump(), ensure_ascii=True),
        },
    ]

    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        response_format={"type": "json_object"},
    )

    content = completion.choices[0].message.content
    if not content:
        raise RuntimeError("No content returned by the model.")

    rewritten = ExamQuestion.model_validate_json(content)
    return rewritten.model_dump_json(indent=2, ensure_ascii=True)
