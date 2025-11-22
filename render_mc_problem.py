from jinja2 import Environment, FileSystemLoader
from data_model import MultipleChoiceExamQuestion
import os
import unicodedata

from render_problem import fix_latex_filter
from text_utils import strip_non_ascii

def strip_non_ascii(text):
    """Remove or replace non-ASCII characters with ASCII equivalents."""
    if not text:
        return text
    
    # First try to normalize to ASCII equivalents
    normalized = unicodedata.normalize('NFKD', text)
    # Encode to ASCII, replacing non-ASCII with closest equivalent or removing
    ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
    return ascii_text



def render_mc_problem(exam_question: MultipleChoiceExamQuestion, problem_number: int, template_path: str = "templates/mc_problem_template.jinja2") -> str:
    """
    Render a MultipleChoiceExamQuestion to LaTeX using the Jinja template.
    
    Args:
        exam_question: The MultipleChoiceExamQuestion instance to render
        problem_number: The problem number to display in the title
        template_path: Path to the Jinja template file
        
    Returns:
        Rendered LaTeX string
    """
    # Set up Jinja environment
    template_dir = os.path.dirname(os.path.abspath(template_path))
    template_name = os.path.basename(template_path)
    
    env = Environment(loader=FileSystemLoader(template_dir))
    
    # Add custom filter to handle non-ASCII characters
    
    env.filters['fix_text'] = fix_latex_filter
    
    template = env.get_template(template_name)
    
    # Prepare template context
    context = {
        'problem_number': problem_number,
        'sub_questions': enumerate(exam_question.sub_questions, start=1),
        'enumerate': enumerate,  # Make enumerate available in template
    }
    
    # Render and return
    return template.render(context)
