from typing import List, Optional
from pydantic import BaseModel

class SubQuestion(BaseModel):
    question_text_latex: str
    question_answer_latex: str
    available_points: float
    starred: bool = False  # Whether to mark with * (independent subproblem)
    box_height: str = "4cm"  # Height of solution box

class MultipleChoiceSubQuestion(BaseModel):
    question_text_latex: str
    question_options: List[str]
    question_correct_option_indices: List[int]  # Support multiple correct answers
    question_points: float
    calculation_function: str = "binary_mc"
    show_mc_notes: bool = False  # Show instructions on how to mark answers
    show_corrections: bool = False  # Show correction text for wrong answers
    option_corrections: Optional[dict] = None  # Mapping of option index to correction text

class ExamQuestion(BaseModel):

    total_points: int
    sub_questions: List[SubQuestion]
    question_title: Optional[str] = None
    question_description_latex: Optional[str] = None


class MultipleChoiceExamQuestion(BaseModel):
    total_points: int
    sub_questions: List[MultipleChoiceSubQuestion]
    question_title: Optional[str] = None
    question_description_latex: Optional[str] = r"\begin{center}\mcnotes{}\end{center}"
    
class ExamContent(BaseModel):
    problems: List[ExamQuestion | MultipleChoiceExamQuestion]

class Exam(BaseModel):
    total_points: int
    total_time_min: int
    exam_content: ExamContent
    exam_title: str
    examiner: str
    module: str
    start_time: str
    end_time: str
    exam_chair: str

