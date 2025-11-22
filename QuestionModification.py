import json
import os
from pathlib import Path
from typing import Iterable, Optional

from openai import OpenAI

from data_model import ExamQuestion, SubQuestion


SYSTEM_PROMPT_SUBQUESTION = """
You generate a new single sub-question based on an old question you get provided.
Input JSON contains: question_text_latex, question_answer_latex, available_points, variation (0-10).
0 means only adjust numbers while keeping wording and task essentially identical; 10 means a completely new task while keeping the same difficulty and amount of work needed to solve.
Rewrite according to the variation level and update question_answer_latex accordingly.
Respond ONLY with JSON: {"question_text_latex": "...", "question_answer_latex": "..."}.
"""

SYSTEM_PROMPT_TITLE_DESC = """
You rewrite the title and description for a block of sub-questions.
Input JSON contains: question_title, question_description_latex, variation (0-10), and the list of sub_questions with their texts and points.
0 means keep title/description almost identical (only adjust numbers), 10 means completely new question while keeping difficulty aligned with the sub-questions.
Respond ONLY with JSON: {"question_title": "...", "question_description_latex": "..."}.
IMPORTANT:
- Include the concrete givens/objects/parameters from the provided sub-questions or description (e.g., function definitions, constants, bounds).
- Avoid generic phrases like "verbundene Schritte" or "connected steps"; be specific about what the block covers.
- Keep it concise but informative for the subsequent sub-questions.
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
    variation: int,
    context_sub_questions: list[SubQuestion],
    question_context: dict | None = None,
) -> SubQuestion:
    """Send only minimal sub-question content to the model and return rewritten fields."""
    payload = {
        "question_text_latex": sub_question.question_text_latex,
        "question_answer_latex": sub_question.question_answer_latex,
        "available_points": sub_question.available_points,
        "variation": variation,
        "question_context": question_context or {},
        "previous_sub_questions": [
            {
                "question_text_latex": cq.question_text_latex,
                "question_answer_latex": cq.question_answer_latex,
                "available_points": cq.available_points,
            }
            for cq in context_sub_questions
        ],
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
    variation: int = 5,
    client: Optional[OpenAI] = None,
) -> ExamQuestion:
    """Rewrite a single ExamQuestion instance and return the rewritten instance."""
    client = client or _client()
    variation = max(0, min(variation, 10))

    def _rewrite_title_description() -> dict:
        payload = {
            "question_title": exam_question.question_title or "",
            "question_description_latex": exam_question.question_description_latex
            or "",
            "variation": variation,
            "sub_questions": [
                {
                    "question_text_latex": sq.question_text_latex,
                    "available_points": sq.available_points,
                }
                for sq in exam_question.sub_questions
            ],
        }
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_TITLE_DESC},
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
            return {
                "question_title": exam_question.question_title,
                "question_description_latex": exam_question.question_description_latex,
            }
        return json.loads(content)

    # First rewrite title/description to capture the starting context.
    title_desc = _rewrite_title_description()
    rewritten_sub_questions: list[SubQuestion] = []
    for sub_q in exam_question.sub_questions:
        rewritten_sub_questions.append(
            _rewrite_sub_question(
                sub_q,
                model=model,
                temperature=temperature,
                client=client,
                variation=variation,
                # Use already rewritten predecessors as context to keep the block coherent.
                context_sub_questions=rewritten_sub_questions,
                # Pass rewritten title/description to each sub-question.
                question_context={
                    "question_title": title_desc.get(
                        "question_title", exam_question.question_title
                    ),
                    "question_description_latex": title_desc.get(
                        "question_description_latex",
                        exam_question.question_description_latex,
                    ),
                },
            )
        )

    return _copy_model(
        exam_question,
        update={
            "sub_questions": rewritten_sub_questions,
            "question_title": title_desc.get(
                "question_title", exam_question.question_title
            ),
            "question_description_latex": title_desc.get(
                "question_description_latex",
                exam_question.question_description_latex,
            ),
        },
    )
