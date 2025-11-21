from typing import List
from pydantic import BaseModel

class SubQuestion(BaseModel):
    question_text_latex: str
    question_answer_latex: str
    available_points: float

class ExamQuestion(BaseModel):

    total_points: int
    sub_questions: List[SubQuestion]

class Exam(BaseModel):

    total_points: int
    total_time_min: int

    exercises: List[ExamQuestion]

