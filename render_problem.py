from jinja2 import Environment, FileSystemLoader
from text_utils import strip_non_ascii
from data_model import ExamQuestion
import os
import unicodedata
import subprocess
import tempfile
import os
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def fix_latex_with_llm(latex_str: str, error: str) -> str | None:
    """
    Uses an LLM to fix invalid LaTeX code.
    """
    prompt = f"""The following LaTeX code is invalid and fails to compile. Please fix it.
Only return the corrected LaTeX code, without any explanation. Do not turn it into a full document, just fix the code as is. Only fix syntax errors, ensure the structure is correct.
If there are some broken figures / plots, simply remove them.

Invalid LaTeX:
---
{latex_str}
---

Error Message:
---
{error}
---

Corrected LaTeX:
"""
    try:
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a LaTeX expert."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        if response.choices[0].message.content:
            fixed_latex = response.choices[0].message.content.strip()
            return fixed_latex
        return None
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None

def latex_is_valid(latex_str: str) -> tuple[bool, str]:
    """Check if LaTeX code compiles successfully by creating a minimal document."""
    
    minimal_latex_doc = r"""
\documentclass{article}
\usepackage{amsmath}
\usepackage{graphicx}
\usepackage{amssymb}
% Add any other packages that are commonly used in your snippets
\begin{document}
""" + latex_str + r"""
\end{document}
"""

    with tempfile.TemporaryDirectory() as tmp:
        tex_path = os.path.join(tmp, "test.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(minimal_latex_doc)
        
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "-output-directory", tmp, tex_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if result.returncode == 0:
            return True, ""
        else:
            log_path = os.path.join(tmp, "test.log")
            error_log = ""
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    error_log = f.read()
            except FileNotFoundError:
                error_log = result.stdout.decode('utf-8', errors='ignore') + "\n" + result.stderr.decode('utf-8', errors='ignore')
            print("LaTeX compilation error log:")
            print(error_log)
            return False, error_log
#     

def fix_latex_filter(text):
    is_valid, error = latex_is_valid(text)
    if is_valid:
        return text
    else:
        print("Rendered LaTeX is not valid. Attempting to fix with LLM...")
        fixed_latex = fix_latex_with_llm(text, error)
        
        max_attempts = 3
        current_latex = fixed_latex
        
        for attempt in range(1, max_attempts + 1):
            
            is_valid, error = latex_is_valid(current_latex) if current_latex else (False, "")
            if current_latex and is_valid:
                print(f"LLM fixed the LaTeX successfully on attempt {attempt}.")
                return current_latex
            elif attempt < max_attempts:
                print(f"Attempt {attempt} failed. Retrying...")
                current_latex = fix_latex_with_llm(current_latex if current_latex else rendered_latex, error)
            else:
                print(f"LLM could not fix the LaTeX after {max_attempts} attempts. The output is not valid.")
                return ""
    return text
            
def render_problem(exam_question: ExamQuestion, problem_number: int, template_path: str = "templates/problem_template.jinja2") -> str | None:
    """
    Render an ExamQuestion to LaTeX using the Jinja template.
    
    Args:
        exam_question: The ExamQuestion instance to render
        problem_number: The problem number to display in the title
        template_path: Path to the Jinja template file
        
    Returns:
        Rendered LaTeX string
    """
    # Set up Jinja environment
    template_dir = os.path.dirname(os.path.abspath(template_path))
    template_name = os.path.basename(template_path)
    
    env = Environment(loader=FileSystemLoader(template_dir))
    


    
    env.filters['fix_latex_filter'] = fix_latex_filter
    
    template = env.get_template(template_name)
    
    
    # Prepare template context
    context = {
        'problem_number': problem_number,
        'question_title': exam_question.question_title,
        'question_description_latex': exam_question.question_description_latex,
        'sub_questions': enumerate(exam_question.sub_questions, start=1),
    }
    
    rendered_latex = template.render(context)
    
    # is_valid, error = latex_is_valid(rendered_latex)
    # # if not is_valid:
    # #     print("Rendered LaTeX is not valid. Attempting to fix with LLM...")
    # #     print(error)
    # #     return None
    
    return rendered_latex