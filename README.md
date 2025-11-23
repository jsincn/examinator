# Examinator - AI-Powered Exam Processing & Generation System

## Inspiration

As students, we've all struggled with finding quality practice exams that match the format and difficulty of actual university exams. Professors often provide past exams, but these are typically one-time use resources. We wanted to create a tool that could:

- Transform past exam PDFs into reusable practice materials
- Automatically generate solution keys with detailed explanations
- Create new exam variations to prevent memorization
- Help students practice with exams that mirror the actual exam format and complexity

Examinator was born from the need to democratize access to high-quality exam preparation materials, making it easier for students to practice effectively and succeed in their courses.

## What it does

Examinator is an intelligent exam processing system that takes past exam PDFs and transforms them into comprehensive practice materials. Here's what it does:

1. **PDF Parsing & Extraction**: Uses vision-enabled LLMs to extract exam metadata (title, module, points, time) and all questions from uploaded PDF files, handling complex LaTeX-formatted mathematical content.

2. **Ensemble Problem Solving**: Employs a sophisticated ensemble system with three independent solver LLMs that work in parallel to solve each question. An arbiter LLM evaluates their agreement and selects the best answer, ensuring accuracy through consensus.

3. **Solution Key Generation**: Automatically generates detailed solution keys with point distributions, matching the style of official exam solutions.

4. **Professional PDF Rendering**: Uses LaTeX templates to generate beautifully formatted exam and solution PDFs that match university exam standards.

5. **Question Variation**: Can generate variations of multiple-choice questions with different numbers and contexts while maintaining the same difficulty level.

6. **RAG-Enhanced Context**: Optionally uses Retrieval-Augmented Generation (RAG) to retrieve relevant course material context when generating new questions.

## How we built it

**Architecture Overview:**
- **Frontend**: Streamlit web application with a clean, Apple-inspired UI
- **Backend**: Python-based processing pipeline
- **LLM Integration**: Different OpenAI Models for vision, parsing, problem solving and cross-verification
- **Data Models**: Pydantic models for type-safe exam data (Unified Exam Format - UEF)
- **PDF Processing**: PyMuPDF for PDF parsing and LaTeX for rendering

**Key Components:**

1. **PDF Parser** (`parsing_new.py`): 
   - Extracts exam metadata from cover pages using vision models
   - Parses question content from all pages
   - Handles LaTeX formatting and mathematical notation

2. **Ensemble Solver** (`ensemble_solver.py`):
   - Three independent Solver LLMs solve problems in parallel
   - Arbiter LLM evaluates semantic agreement between solutions
   - Implements iterative rephrasing for ambiguous questions
   - Normalizes answers to handle LaTeX formatting differences

3. **Exam Builder** (`build_exam.py`):
   - Renders exams using Jinja2 templates
   - Generates LaTeX source files
   - Compiles to professional PDFs using TUM exam template

4. **RAG Pipeline** (`ragpipeline.py`):
   - ChromaDB vector database for course material storage
   - Semantic search for relevant context
   - Enhances question generation with course-specific knowledge

5. **Data Models** (`data_model.py`):
   - Type-safe Pydantic models for exam structure
   - Supports both regular and multiple-choice questions
   - Validates exam data integrity

## How to run
1. Ensure that you have a full latex installation avaialble (either through mactex or texlive-full).
2. Clone this repo
```
git clone git@github.com:jsincn/examinator.git
```
3. Set up and activate a virtual environment
Either use `venv` or your favorite other solution.
```
python -m venv .venv
source .venv/bin/activate
```
4. Install requirements
```
pip install -r requirements.txt
```
5. Set your `OPENAI_API_KEY` environment variable
5. Run Streamlit
```
streamlit run app.py
```

