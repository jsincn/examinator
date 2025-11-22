#!/usr/bin/env python3
"""Test script to create an Exam object and build a PDF."""

from data_model import Exam, ExamQuestion, SubQuestion
from build_exam import build_exam

# Create some arbitrary sub-questions
sub_question_1 = SubQuestion(
    question_text_latex="What is the time complexity of binary search?",
    question_answer_latex="O(log n)",
    available_points=2.0
)

sub_question_2 = SubQuestion(
    question_text_latex="Explain the difference between a stack and a queue.",
    question_answer_latex="A stack follows LIFO (Last In First Out) principle, while a queue follows FIFO (First In First Out) principle.",
    available_points=3.0
)

sub_question_3 = SubQuestion(
    question_text_latex="What is the purpose of dynamic programming?",
    question_answer_latex="Dynamic programming is used to solve optimization problems by breaking them down into simpler subproblems and storing the results to avoid redundant computations.",
    available_points=5.0
)

# Create exam questions
question_1 = ExamQuestion(
    total_points=5,
    sub_questions=[sub_question_1, sub_question_2]
)

question_2 = ExamQuestion(
    total_points=5,
    sub_questions=[sub_question_3]
)

# Create the exam
exam = Exam(
    total_points=10,
    total_time_min=90,
    problems=[question_1, question_2],
    exam_title="Introduction to Algorithms - Midterm Exam",
    examiner="Prof. Dr. John Smith",
    module="CS101",
    start_time="2025-12-01 10:00",
    end_time="2025-12-01 11:30",
    exam_chair="Chair of Computer Science"
)

# Build the exam PDF
print("Building exam PDF...")
pdf_path = build_exam(exam)
print(f"PDF successfully generated at: {pdf_path}")
