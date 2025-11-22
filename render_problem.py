from jinja2 import Environment, FileSystemLoader
from data_model import ExamQuestion
import os
import unicodedata

def strip_non_ascii(text):
    """Remove or replace non-ASCII characters with ASCII equivalents."""
    if not text:
        return text
    
    # First try to normalize to ASCII equivalents
    normalized = unicodedata.normalize('NFKD', text)
    # Encode to ASCII, replacing non-ASCII with closest equivalent or removing
    ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
    return ascii_text

def render_problem(exam_question: ExamQuestion, problem_number: int, template_path: str = "templates/problem_template.jinja2") -> str:
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
    
    # Add custom filter to handle escaped newlines
    def fix_newlines(text):
        if text:
            # Strip non-ASCII characters first
            text = strip_non_ascii(text)
            # Replace literal \n with LaTeX line breaks
            text = text.replace('\\n', '\n\n')
            
            # Fix unclosed itemize/enumerate environments
            # Count opening and closing tags
            begin_itemize = text.count(r'\begin{itemize}')
            end_itemize = text.count(r'\end{itemize}')
            begin_enumerate = text.count(r'\begin{enumerate}')
            end_enumerate = text.count(r'\end{enumerate}')
            
            # Close any unclosed environments
            if begin_itemize > end_itemize:
                text += '\n' + r'\end{itemize}' * (begin_itemize - end_itemize)
            if begin_enumerate > end_enumerate:
                text += '\n' + r'\end{enumerate}' * (begin_enumerate - end_enumerate)
                
        return text
    
    env.filters['fix_newlines'] = fix_newlines
    
    template = env.get_template(template_name)
    
    # Prepare template context
    context = {
        'problem_number': problem_number,
        'question_title': exam_question.question_title,
        'question_description_latex': exam_question.question_description_latex,
        'sub_questions': enumerate(exam_question.sub_questions, start=1),
    }
    
    # Render and return
    return template.render(context)
