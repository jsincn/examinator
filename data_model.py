from typing import List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

class SubQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")  
    question_text_latex: str
    question_answer_latex: str
    available_points: float
    starred: bool = False  # Whether to mark with * (independent subproblem)
    box_height: str = "4cm"  # Height of solution box

class MultipleChoiceSubQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")  
    question_text_latex: str
    question_options: List[str]
    question_correct_option_indices: List[int]  # Support multiple correct answers
    question_points: float
    calculation_function: str = "binary_mc"
    show_mc_notes: bool = False  # Show instructions on how to mark answers
    show_corrections: bool = False  # Show correction text for wrong answers
    option_corrections: List[str] = Field(default_factory=list)  # List of corrections, one per option (empty string if no correction)

class ExamQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")  

    total_points: int
    sub_questions: List[SubQuestion]
    question_title: Optional[str] = None
    question_description_latex: Optional[str] = None


class MultipleChoiceExamQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")  

    total_points: int
    sub_questions: List[MultipleChoiceSubQuestion]
    question_title: str = ""
    question_description_latex: str = ""
    
class ExamContent(BaseModel):
    model_config = ConfigDict(extra="forbid")  

    problems: List[ExamQuestion | MultipleChoiceExamQuestion]

class Exam(BaseModel):
    model_config = ConfigDict(extra="forbid")  
    
    total_points: int
    total_time_min: int
    exam_content: ExamContent
    exam_title: str
    examiner: str
    module: str
    start_time: str
    end_time: str
    exam_chair: str


class ExamMetadataOnly(BaseModel):
    model_config = ConfigDict(extra="forbid")  # ← NEUE ZEILE

    total_points: int
    total_time_min: int
    exam_title: str
    examiner: str
    module: str
    start_time: str = "00:00"
    end_time: str = "00:00"
    exam_chair: str = "Unknown"