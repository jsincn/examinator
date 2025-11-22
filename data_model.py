from typing import List, Optional
from pydantic import BaseModel, ConfigDict



class OptionCorrection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pass 

class SubQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")  
    
    question_text_latex: str
    question_answer_latex: str
    available_points: float
    starred: bool = False
    box_height: str = "4cm"

class MultipleChoiceSubQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")  
    
    question_text_latex: str
    question_options: List[str]
    question_correct_option_indices: List[int]
    question_points: float
    calculation_function: str = "binary_mc"
    show_mc_notes: bool = False
    show_corrections: bool = False
    option_corrections: Optional[OptionCorrection] = None

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
    question_title: Optional[str] = None
    show_instructions: bool = True
    option_corrections: Optional[OptionCorrection] = None

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