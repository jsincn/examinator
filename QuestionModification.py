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
) -> SubQuestion:
    """Send only minimal sub-question content to the model and return rewritten fields."""
    context_info = ""
    if context_sub_questions:
        context_info = "\n\nPrevious sub-questions in this exam question:\n"
        for i, cq in enumerate(context_sub_questions, 1):
            context_info += f"\n{i}. {cq.question_text_latex}"
            context_info += f"\n   Answer: {cq.question_answer_latex}"
            context_info += f"\n   Points: {cq.available_points}\n"

    user_prompt = f"""Generate a new sub-question based on the following:

Original question: {sub_question.question_text_latex}
Original answer: {sub_question.question_answer_latex}
Available points: {sub_question.available_points}
Variation level: {variation}/10

Variation guide:
- 0: Only adjust numbers, keep wording and task identical
- 5: Moderate changes to wording and approach, same difficulty
- 10: Completely new task, same difficulty and workload{context_info}

Respond ONLY with JSON: {{"question_text_latex": "...", "question_answer_latex": "..."}}"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_SUBQUESTION},
        {"role": "user", "content": user_prompt},
    ]

    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=messages,
        temperature=temperature,
        response_format=SubQuestion,  # Hilfsmodell
    )

    parsed = response.choices[0].message.parsed
    if not parsed:
        raise RuntimeError("Failed to parse rewritten sub-question from model response.")

    update_payload = {
        "question_text_latex": parsed.question_text_latex,
        "question_answer_latex": parsed.question_answer_latex,
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
            )
        )

    return _copy_model(exam_question, update={"sub_questions": rewritten_sub_questions})
