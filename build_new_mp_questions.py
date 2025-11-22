import os
from openai import OpenAI
from data_model import MultipleChoiceExamQuestion
import streamlit as st

def generate_exam_question_with_openai(
    original_question: MultipleChoiceExamQuestion,
    variation_instruction: str = "Generate a similar question with different numbers and context",
    variation: int = 5,
    temperature: float = 0.7,
) -> MultipleChoiceExamQuestion:

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    import json
    original_json = json.dumps(original_question.model_dump(), indent=2)

    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert exam question generator.\n"
                "Your ONLY task is to output valid JSON that matches the provided schema.\n"
                "RULES:\n"
                "1. Output ONLY JSON. No prose, no explanations.\n"
                "2. The JSON must match the exact Pydantic schema of MultipleChoiceExamQuestion.\n"
                "3. All LaTeX must be inside double-quoted strings and escape backslashes.\n"
                "4. Never include comments, Markdown, or text outside the JSON.\n"
                "5. Every sub-question must have the same number of options as in the input.\n"
                "6. correct_option_indices must be 0-indexed and valid.\n"
                "7. Always include all required fields, even if empty.\n"
                "8. Variation level (0-10): 0 = adjust numbers only, keep wording almost identical, 10 completely new question (based on Course Material if provided); "
                "10 = completely new phrasing/context but same concept and difficulty. Use the provided variation value.\n"
            )
        },
        {
            "role": "user",
            "content": (
                "Here is an example of a valid JSON structure:\n"
                "{\n"
                '  "total_points": 10,\n'
                '  "sub_questions": [\n'
                "    {\n"
                '      "question_text_latex": "What is 2+2?",\n'
                '      "question_options": ["1", "4", "5"],\n'
                '      "question_correct_option_indices": [1],\n'
                '      "question_points": 10,\n'
                '      "calculation_function": "binary_mc",\n'
                '      "show_mc_notes": false,\n'
                '      "show_corrections": false,\n'
                '      "option_corrections": ["", "Correct.", ""]\n'
                "    }\n"
                "  ],\n"
                '  "question_title": "Example",\n'
                '  "question_description_latex": ""\n'
                "}\n\n"
                "Now produce a NEW variation based on the following original question:\n\n"
                f"{original_json}\n\n"
                f"Variation instructions: {variation_instruction}\n"
                f"Variation level: {max(0, min(variation, 10))}\n\n"
                "Return ONLY valid JSON matching the schema."
            )
        }
    ]

    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=messages,
        temperature=temperature,
        response_format=MultipleChoiceExamQuestion,
    )

    parsed = response.choices[0].message.parsed
    if parsed is None:
        raise ValueError("OpenAI API returned no parsed content")
    return parsed


def modify_mp_questions(exam_question: MultipleChoiceExamQuestion):
    """Generate new multiple-choice exam questions based on existing ones."""
    return generate_exam_question_with_openai(exam_question)
