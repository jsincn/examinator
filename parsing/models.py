from pydantic import BaseModel, Field
from typing import List, Optional 

#Schema - UNIFIED EXAM FORMAT

class SubQuestion(BaseModel):
    #"..." = Pflichtfeld
    question_text_latex: str = Field(..., description="The text of the sub-question using LaTeX.")
    question_answer_latex: str = Field(..., description="The solution found in the document.")
    available_points: float = Field(..., description="Points for this sub-question.")

class ExamQuestion(BaseModel):
    # optional title weil es in der UEF nicht gelistet war 
    title: Optional[str] = Field(None, description="Title of the question (e.g. 'Problem 1: Logic'). If not visible, leave null.")
    
    total_points: int = Field(..., description="Total points for this exercise.")
    sub_questions: List[SubQuestion] = Field(..., description="List of sub-questions.")

class Exam(BaseModel):
    total_points: int = Field(..., description="Total points.")
    total_time_min: int = Field(..., description="Time in minutes.")
    exercises: List[ExamQuestion] = Field(..., description="List of exercises.")