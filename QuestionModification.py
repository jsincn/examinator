import json
import os
from pathlib import Path
from typing import Iterable, Optional

from openai import OpenAI

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


def _rewrite_sub_question(
    sub_question: dict,
    *,
    model: str,
    temperature: float,
    client: OpenAI,
) -> dict:
    """Send only minimal sub-question content to the model and return rewritten fields."""
    payload = {
        "question_text_latex": sub_question.get("question_text_latex", ""),
        "question_answer_latex": sub_question.get("question_answer_latex", ""),
        "available_points": sub_question.get("available_points", None),
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
    # Keep all original keys, replace only the rewritten ones.
    updated = dict(sub_question)
    updated["question_text_latex"] = rewritten_fields.get(
        "question_text_latex", sub_question.get("question_text_latex", "")
    )
    updated["question_answer_latex"] = rewritten_fields.get(
        "question_answer_latex", sub_question.get("question_answer_latex", "")
    )
    return updated


def rewrite_exam_question_json(
    exam_question_json: str,
    *,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    client: Optional[OpenAI] = None,
) -> str:
    """
    Rewrite a single ExamQuestion JSON and return the rewritten JSON string.
    Only the sub-question text/answers are sent to the model; structure is preserved locally.
    """
    exam_question = json.loads(exam_question_json)
    client = client or _client()

    rewritten_sub_questions = []
    for sub_q in exam_question.get("sub_questions", []):
        rewritten_sub = _rewrite_sub_question(
            sub_q, model=model, temperature=temperature, client=client
        )
        rewritten_sub_questions.append(rewritten_sub)

    updated_question = dict(exam_question)
    updated_question["sub_questions"] = rewritten_sub_questions
    return json.dumps(updated_question, indent=2, ensure_ascii=True)


def rewrite_uef_exam(
    exam: dict,
    *,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    client: Optional[OpenAI] = None,
) -> dict:
    """
    Rewrite every ExamQuestion in a UEF-style exam object (with an 'exercises' list).
    Each question is rewritten via rewrite_exam_question_json (one LLM call per question).
    Returns the updated exam dict.
    """
    exercises = exam.get("exercises", [])
    client = client or _client()

    rewritten_exercises = []
    for exercise in exercises:
        rewritten = rewrite_exam_question_json(
            json.dumps(exercise, ensure_ascii=True),
            model=model,
            temperature=temperature,
            client=client,
        )
        rewritten_exercises.append(json.loads(rewritten))

    exam = dict(exam)
    exam["exercises"] = rewritten_exercises
    return exam


def rewrite_uef_exam_json(
    exam_json: str,
    *,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    client: Optional[OpenAI] = None,
) -> str:
    """
    Take a full UEF exam JSON (with exercises list) and rewrite every ExamQuestion,
    one LLM call per question. Returns the updated exam JSON string.
    """
    exam = json.loads(exam_json)
    rewritten_exam = rewrite_uef_exam(
        exam, model=model, temperature=temperature, client=client
    )
    return json.dumps(rewritten_exam, indent=2, ensure_ascii=True)
