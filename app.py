import streamlit as st
from data_model import (
    Exam,
    ExamContent,
    ExamQuestion,
    SubQuestion,
    MultipleChoiceExamQuestion,
    MultipleChoiceSubQuestion,
)
from build_exam import build_exam
from dotenv import load_dotenv

from parsing_new import parse_exam_complete

load_dotenv()


def get_dummy_exam():
    """Create a dummy exam for testing."""
    # Create some arbitrary sub-questions
    mc_sub_question_1 = MultipleChoiceSubQuestion(
        question_text_latex="What is the capital of France?",
        question_options=["Berlin", "Madrid", "Paris", "Rome"],
        question_correct_option_indices=[2],
        question_points=1,
        calculation_function="binary_mc",
        show_mc_notes=False,
        show_corrections=True,
    )

    mc_sub_question_2 = MultipleChoiceSubQuestion(
        question_text_latex="Which of the following are programming languages?",
        question_options=["Python", "HTML", "Java", "CSS"],
        question_correct_option_indices=[0, 2],
        question_points=2,
        calculation_function="mc",
        show_mc_notes=False,
        show_corrections=True,
    )

    mc_question_1 = MultipleChoiceExamQuestion(
        total_points=1,
        sub_questions=[mc_sub_question_1, mc_sub_question_2],
        question_title="Multiple Choice Questions",
        question_description_latex=r"\begin{center}\mcnotes{}\end{center}",
    )

    sub_question_1 = SubQuestion(
        question_text_latex="What is the time complexity of binary search?",
        question_answer_latex="O(log n)",
        available_points=2.0,
    )

    sub_question_2 = SubQuestion(
        question_text_latex="Explain the difference between a stack and a queue.",
        question_answer_latex="A stack follows LIFO (Last In First Out) principle, while a queue follows FIFO (First In First Out) principle.",
        available_points=3.0,
    )

    sub_question_3 = SubQuestion(
        question_text_latex="What is the purpose of dynamic programming?",
        question_answer_latex="Dynamic programming is used to solve optimization problems by breaking them down into simpler subproblems and storing the results to avoid redundant computations.",
        available_points=5.0,
    )

    # Create exam questions
    question_1 = ExamQuestion(
        total_points=5,
        sub_questions=[sub_question_1, sub_question_2],
        question_title="Short Answer Questions",
        question_description_latex=r"""\begin{center}Please answer the following questions concisely.\end{center}""",
    )

    question_2 = ExamQuestion(
        total_points=5,
        sub_questions=[sub_question_3],
        question_title="Dynamic Programming Question",
        question_description_latex=r"""\begin{center}Answer the following question in detail.\end{center}""",
    )

    # Create the exam
    exam = Exam(
        total_points=10,
        total_time_min=90,
        exam_content=ExamContent(problems=[mc_question_1, question_1, question_2]),
        exam_title="Introduction to Algorithms - Midterm Exam",
        examiner="Prof. Dr. John Smith",
        module="CS101",
        start_time="2025-12-01 10:00",
        end_time="2025-12-01 11:30",
        exam_chair="Chair of Computer Science",
    )

    return exam


# Configure page
st.set_page_config(layout="wide")

# Create columns for layout
left_col, right_col = st.columns([1, 2])

# Left column - file upload
with left_col:
    st.header("Upload File")
    uploaded_file = st.file_uploader("Choose a file", type=["pdf"])

    if uploaded_file is not None:
        st.success(f"Uploaded: {uploaded_file.name}")

        # Build the exam with dummy data only if not already built
        if st.session_state.get("uploaded_file") != uploaded_file.name:
            with st.spinner("Building exam PDF..."):

                exam = parse_exam_complete(uploaded_file)
                # exam = get_dummy_exam()

                st.write(exam)

                exam_path, solution_path = build_exam(exam)

                # Read the PDF file
                with open(exam_path, "rb") as pdf_file:
                    pdf_bytes = pdf_file.read()

                with open(solution_path, "rb") as solution_file:
                    solution_bytes = solution_file.read()

                # Store PDFs in session state
                st.session_state["exam_pdf"] = pdf_bytes
                st.session_state["solution_pdf"] = solution_bytes
                st.session_state["uploaded_file"] = uploaded_file.name

                st.success("Exam PDF generated successfully!")

        # Display download buttons if PDFs are available in session state
        if "exam_pdf" in st.session_state and "solution_pdf" in st.session_state:
            st.download_button(
                label="Download Exam PDF",
                data=st.session_state["exam_pdf"],
                file_name="exam.pdf",
                mime="application/pdf",
            )
            st.download_button(
                label="Download Solution PDF",
                data=st.session_state["solution_pdf"],
                file_name="solution.pdf",
                mime="application/pdf",
            )