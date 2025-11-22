import json
import os
from pathlib import Path
from typing import Iterable, Optional

from openai import OpenAI

from data_model import ExamQuestion, SubQuestion


SYSTEM_PROMPT_SUBQUESTION = """
You rewrite a single sub-question.
Input JSON contains: question_text_latex, question_answer_latex, available_points.
Rewrite the wording and adjust numbers if needed but keep the same concept and difficulty.
Update question_answer_latex accordingly.
Respond ONLY with JSON: {"question_text_latex": "...", "question_answer_latex": "..."}.
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


def _copy_model(obj, update: dict):
    """Compatibility helper for pydantic v1/v2 copy semantics."""
    if hasattr(obj, "model_copy"):
        return obj.model_copy(update=update)
    return obj.copy(update=update)


def _rewrite_sub_question(
    sub_question: SubQuestion,
    *,
    model: str,
    temperature: float,
    client: OpenAI,
) -> SubQuestion:
    """Send only minimal sub-question content to the model and return rewritten fields."""
    payload = {
        "question_text_latex": sub_question.question_text_latex,
        "question_answer_latex": sub_question.question_answer_latex,
        "available_points": sub_question.available_points,
    }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_SUBQUESTION},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=True)},
    ]

    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        response_format={"type": "json_object"},
    )

    content = completion.choices[0].message.content
    if not content:
        raise RuntimeError("No content returned by the model for sub-question.")

    rewritten_fields = json.loads(content)
    update_payload = {
        "question_text_latex": rewritten_fields.get(
            "question_text_latex", sub_question.question_text_latex
        ),
        "question_answer_latex": rewritten_fields.get(
            "question_answer_latex", sub_question.question_answer_latex
        ),
    }
    return _copy_model(sub_question, update=update_payload)


def rewrite_exam_question(
    exam_question: ExamQuestion,
    *,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    client: Optional[OpenAI] = None,
) -> ExamQuestion:
    """Rewrite a single ExamQuestion instance and return the rewritten instance."""
    client = client or _client()

    rewritten_sub_questions = [
        _rewrite_sub_question(sub_q, model=model, temperature=temperature, client=client)
        for sub_q in exam_question.sub_questions
    ]

    return _copy_model(exam_question, update={"sub_questions": rewritten_sub_questions})


