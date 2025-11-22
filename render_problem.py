from jinja2 import Environment, FileSystemLoader
from data_model import ExamQuestion
import os

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
    template = env.get_template(template_name)
    
    # Prepare template context
    context = {
        'problem_number': problem_number,
        'sub_questions': enumerate(exam_question.sub_questions, start=1),
    }
    
    # Render and return
    return template.render(context)
