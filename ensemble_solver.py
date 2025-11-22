"""
Math-Solver Ensemble System
Coordinates three independent Solver LLMs and an Arbiter LLM
to solve math problems with agreement checking and rephrasing.
Supports Unified Exam Format (UEF) for structured exam processing.
"""

import os
import json
import re
import time
import logging
from collections import Counter
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError

# Import UEF data models
from data_model import Exam, ExamQuestion, SubQuestion, ExamContent, MultipleChoiceExamQuestion

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Solver:
    """Independent Solver LLM that attempts to solve math problems."""
    
    def __init__(self, model: str, name: str, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize a Solver instance.
        
        Args:
            model: OpenAI model name to use
            name: Human-readable name for this solver
            max_retries: Maximum number of retry attempts for API calls
            retry_delay: Initial delay between retries (exponential backoff)
        """
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.name = name
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def _call_api_with_retry(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> str:
        """
        Call OpenAI API with retry logic and exponential backoff.
        
        Args:
            messages: List of message dicts for the API call
            temperature: Temperature setting for the API call
        
        Returns:
            Response content string
        
        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"{self.name} attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"{self.name} failed after {self.max_retries} attempts: {e}")
        
        raise last_exception or Exception("Unknown error in API call")
    
    def solve(self, problem: str, is_latex: bool = False) -> Tuple[str, str]:
        """
        Solve a math problem and return answer and explanation.
        
        Args:
            problem: The problem text (can be LaTeX formatted)
            is_latex: Whether the problem contains LaTeX formatting
        
        Returns:
            Tuple of (answer, explanation)
        """
        latex_note = "\nNote: The problem may contain LaTeX formatting. Interpret it correctly." if is_latex else ""
        
        prompt = f"""You are a math-specialist model. Solve the following problem.

Show only a short explanation. Final answer at the bottom in the format:

Final Answer: <answer>

If the answer should be in LaTeX format, provide it in LaTeX.{latex_note}

Problem:
{problem}"""
        
        messages = [
            {"role": "system", "content": "You are a math-specialist model. Provide clear, concise solutions."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            full_response = self._call_api_with_retry(messages, temperature=0.3)
            
            # Extract final answer
            answer_match = re.search(r'Final Answer:\s*(.+)', full_response, re.IGNORECASE | re.DOTALL)
            if answer_match:
                answer = answer_match.group(1).strip()
            else:
                # Try to extract the last line as answer
                lines = full_response.split('\n')
                answer = lines[-1].strip() if lines else full_response
            
            return answer, full_response
            
        except Exception as e:
            logger.error(f"Error in {self.name}: {e}")
            return "ERROR", f"Error occurred: {str(e)}"


class Arbiter:
    """Arbiter LLM that evaluates solver agreement and correctness."""
    
    def __init__(self, model: str, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize an Arbiter instance.
        
        Args:
            model: OpenAI model name to use
            max_retries: Maximum number of retry attempts for API calls
            retry_delay: Initial delay between retries (exponential backoff)
        """
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def _call_api_with_retry(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        """
        Call OpenAI API with retry logic and exponential backoff.
        
        Args:
            messages: List of message dicts for the API call
            temperature: Temperature setting for the API call
        
        Returns:
            Response content string
        
        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Arbiter attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"Arbiter failed after {self.max_retries} attempts: {e}")
        
        raise last_exception or Exception("Unknown error in API call")
    
    def evaluate(self, problem: str, solver_results: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Evaluate solver results and determine agreement.
        
        Args:
            problem: Original problem statement
            solver_results: List of dicts with 'solver', 'answer', 'explanation'
        
        Returns:
            Dict with agreement status, chosen answer, and rephrasing info
        """
        # Format solver results for the arbiter
        results_text = "\n\n".join([
            f"Solver {i+1} ({result['solver']}):\n"
            f"Answer: {result['answer']}\n"
            f"Explanation: {result['explanation'][:200]}..."  # Truncate long explanations
            for i, result in enumerate(solver_results)
        ])
        
        prompt = f"""Compare the three solver outputs below and determine if they agree.

CRITICAL: Answers are considered to AGREE if they have the SAME MEANING or convey the SAME CONCEPTS, even if worded differently.

Examples of SEMANTIC AGREEMENT (should be marked as agreement=true):
- "improves training speed" = "speeds up convergence" = "accelerates training" (all mean faster training)
- "scaling and shifting" = "scale and shift" = "allows scaling and shifting" (all mean the same operation)
- "batch statistics" = "mini-batch statistics" = "statistics from the batch" (all refer to batch stats)
- "moving averages" = "running averages" = "exponentially weighted averages" (all refer to the same concept)

If they semantically agree → set agreement=true and provide the best-formulated answer.
If they disagree in meaning → set agreement=false and choose the most plausible answer.

Return your decision in JSON format. Start your response with {{ and end with }}:

{{
  "agreement": true/false,
  "chosen_answer": "...",
  "needs_rephrase": true/false,
  "rephrased_question": "..."
}}

Rules:
- Set "agreement" to TRUE if all three answers convey the SAME MEANING/CONCEPTS (semantic equivalence), even with different wording
- Set "agreement" to TRUE if at least 2 out of 3 answers agree in meaning (majority semantic agreement)
- Set "agreement" to FALSE only if answers have genuinely DIFFERENT meanings or concepts
- If agreement is true, set "chosen_answer" to the most complete/well-formulated version
- If agreement is false, set "chosen_answer" to the ACTUAL ANSWER TEXT from the most plausible solver (NOT "Solver 1", but the actual answer content)
- IMPORTANT: "chosen_answer" must be the actual answer text/content, not a reference like "Solver 1" or "Solver 2"
- Set "needs_rephrase" to true only if the question is genuinely ambiguous and rephrasing would help
- If rephrasing, "rephrased_question" must preserve ALL numbers, variables, and mathematical relationships
- Do NOT change any mathematical content, only clarify wording

Original Problem:
{problem}

Solver Results:
{results_text}"""
        
        messages = [
            {"role": "system", "content": "You are an arbiter that evaluates math solutions for semantic equivalence. You understand that answers can be semantically equivalent even if worded differently. You must respond with valid JSON only, starting with { and ending with }."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response_text = self._call_api_with_retry(messages, temperature=0.2)
            
            # Extract JSON from response - handle various formats
            # Remove markdown code blocks if present
            response_text = re.sub(r'```json\s*', '', response_text)
            response_text = re.sub(r'```\s*', '', response_text)
            response_text = response_text.strip()
            
            # Try to extract JSON object if there's extra text
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)
            
            result = json.loads(response_text)
            
            # Validate result structure
            required_keys = ['agreement', 'chosen_answer', 'needs_rephrase', 'rephrased_question']
            for key in required_keys:
                if key not in result:
                    result[key] = False if key == 'agreement' or key == 'needs_rephrase' else ""
            
            # Fix case where arbiter returns "Solver 1", "Solver 2", etc. instead of actual answer
            chosen_answer = result.get('chosen_answer', '')
            if chosen_answer and chosen_answer.strip().lower().startswith('solver'):
                # Try to extract solver number and get the actual answer
                solver_match = re.search(r'solver\s*(\d+)', chosen_answer, re.IGNORECASE)
                if solver_match:
                    solver_num = int(solver_match.group(1))
                    if 1 <= solver_num <= len(solver_results):
                        actual_answer = solver_results[solver_num - 1]['answer']
                        logger.warning(f"Arbiter returned '{chosen_answer}', extracting actual answer from Solver {solver_num}: {actual_answer}")
                        result['chosen_answer'] = actual_answer
                    else:
                        logger.warning(f"Arbiter returned invalid solver reference '{chosen_answer}', using first solver's answer")
                        result['chosen_answer'] = solver_results[0]['answer'] if solver_results else ""
                else:
                    # Fallback to first solver's answer
                    logger.warning(f"Arbiter returned unclear reference '{chosen_answer}', using first solver's answer")
                    result['chosen_answer'] = solver_results[0]['answer'] if solver_results else ""
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"Error parsing arbiter JSON: {e}")
            print(f"Response was: {response_text[:200]}...")
            # Return default response - will use direct agreement check
            return {
                "agreement": False,
                "chosen_answer": solver_results[0]['answer'] if solver_results else "",
                "needs_rephrase": False,
                "rephrased_question": ""
            }
        except Exception as e:
            # Re-raise to let caller handle with direct agreement check
            raise e


class EnsembleCoordinator:
    """Main coordinator for the math-solver ensemble system."""
    
    def __init__(self, max_iterations: int = 3):
        """
        Initialize the ensemble system with three solvers and one arbiter.
        
        Uses cost-effective ChatGPT models for diversity:
        - Solver 1: gpt-4o-mini (cost-effective, good performance)
        - Solver 2: gpt-3.5-turbo (fast, different reasoning, very cheap)
        - Solver 3: gpt-4o-mini (cost-effective alternative)
        - Arbiter: gpt-4o-mini (cost-effective evaluation)
        """
        self.solvers = [
            Solver(model="gpt-4o-mini", name="Solver-1-GPT4oMini"),
            Solver(model="gpt-3.5-turbo", name="Solver-2-GPT35"),
            Solver(model="gpt-4o-mini", name="Solver-3-GPT4oMini")
        ]
        self.arbiter = Arbiter(model="gpt-4o-mini")
        self.max_iterations = max_iterations
    
    def normalize_answer(self, answer: str) -> str:
        """
        Normalize answer for comparison by removing formatting differences.
        
        Handles:
        - LaTeX delimiters ($, \(, \), \[, \])
        - Different multiplication symbols (×, x, *)
        - Whitespace variations
        - Parentheses and spacing in tuples/lists
        - LaTeX commands like \times, \text, etc.
        
        Args:
            answer: Raw answer string to normalize
        
        Returns:
            Normalized string for comparison
        """
        if not answer:
            return ""
        
        normalized = answer
        
        # Remove LaTeX dollar signs
        normalized = normalized.replace('$', '')
        
        # Remove LaTeX inline math delimiters \( and \)
        normalized = re.sub(r'\\?[\(\)]', '', normalized)
        
        # Remove LaTeX display math delimiters \[ and \]
        normalized = re.sub(r'\\?[\[\]]', '', normalized)
        
        # Remove common LaTeX commands (like \times, \text, etc.) but keep their content
        # Handle \times specifically (common in math)
        normalized = re.sub(r'\\times', 'x', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\\text\{([^}]+)\}', r'\1', normalized)  # Extract text from \text{...}
        
        # Remove other LaTeX backslash commands but keep alphanumeric content
        # This handles cases like \frac, \begin, etc.
        normalized = re.sub(r'\\([a-zA-Z]+)', '', normalized)
        
        # Normalize different multiplication symbols (×, x, X, *) to 'x'
        normalized = re.sub(r'[×xX*]', 'x', normalized, flags=re.IGNORECASE)
        
        # Remove remaining backslashes
        normalized = normalized.replace('\\', '')
        
        # Normalize whitespace - collapse multiple spaces/tabs/newlines to single space
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Normalize commas and spacing around them in tuples/lists
        normalized = re.sub(r'\s*,\s*', ',', normalized)
        
        # Normalize equals signs and spacing
        normalized = re.sub(r'\s*=\s*', '=', normalized)
        
        # Normalize parentheses spacing: "( 4, 3, 5, 5 )" -> "(4,3,5,5)"
        normalized = re.sub(r'\(\s+', '(', normalized)
        normalized = re.sub(r'\s+\)', ')', normalized)
        
        # Remove common prefixes like "The output dimensionality is", "Shape:", etc.
        normalized = re.sub(r'^(the\s+(output\s+)?(dimensionality|shape|size)\s+is\s*)', '', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'^(shape\s*[:=]\s*)', '', normalized, flags=re.IGNORECASE)
        
        # Strip and convert to lowercase for comparison
        normalized = normalized.strip().lower()
        
        return normalized
    
    def answers_match(self, answers: List[str]) -> bool:
        """
        Check if answers are essentially the same.
        
        Returns True if:
        - All answers match, OR
        - At least 2 out of 3 answers match (majority agreement)
        """
        if len(answers) < 2:
            return True
        
        normalized = [self.normalize_answer(a) for a in answers]
        
        # Check if all normalized answers are the same
        if all(n == normalized[0] for n in normalized):
            return True
        
        # Check for majority agreement (2 out of 3 match)
        if len(normalized) == 3:
            # Count occurrences of each normalized answer
            counts = Counter(normalized)
            # If any answer appears at least twice, we have majority agreement
            if max(counts.values()) >= 2:
                return True
        
        return False
    
    def solve(self, problem: str, verbose: bool = True, is_latex: Optional[bool] = None) -> Dict[str, Any]:
        """
        Main solving method that coordinates solvers and arbiter.
        
        Args:
            problem: The math problem to solve
            verbose: Whether to print progress information
            is_latex: Whether problem contains LaTeX (auto-detected if None)
        
        Returns:
            Dict with final answer, agreement status, and iteration info
        """
        # Auto-detect LaTeX if not specified
        if is_latex is None:
            is_latex = bool(re.search(r'\\[a-zA-Z]+|\\\(|\\\)|\\\[|\\\]|\$', problem))
        
        current_problem = problem
        iteration = 0
        history = []
        
        while iteration < self.max_iterations:
            iteration += 1
            
            if verbose:
                print(f"\n{'='*60}")
                print(f"Iteration {iteration}")
                print(f"{'='*60}")
                print(f"Problem: {current_problem}\n")
            
            # Get solutions from all three solvers
            solver_results = []
            for solver in self.solvers:
                if verbose:
                    print(f"Querying {solver.name}...")
                
                answer, explanation = solver.solve(current_problem, is_latex=is_latex)
                solver_results.append({
                    'solver': solver.name,
                    'answer': answer,
                    'explanation': explanation
                })
                
                if verbose:
                    print(f"  Answer: {answer}")
            
            # Check for direct agreement (fast, exact/normalized match)
            answers = [r['answer'] for r in solver_results]
            direct_agreement = self.answers_match(answers)
            
            if verbose:
                print(f"\nDirect Agreement Check: {direct_agreement}")
            
            # If we have direct agreement, skip arbiter (saves cost and time)
            # For semantic similarity, let the arbiter LLM handle it
            if direct_agreement:
                arbiter_result = {
                    "agreement": True,
                    "chosen_answer": "",
                    "needs_rephrase": False,
                    "rephrased_question": ""
                }
                arbiter_success = True
                
                # Use the most common answer (majority vote)
                normalized_answers = [self.normalize_answer(a) for a in answers]
                counts = Counter(normalized_answers)
                most_common = counts.most_common(1)[0][0]
                # Find the original answer that matches the most common normalized version
                for answer in answers:
                    if self.normalize_answer(answer) == most_common:
                        arbiter_result['chosen_answer'] = answer
                        break
                else:
                    arbiter_result['chosen_answer'] = answers[0]
                
                if verbose:
                    print(f"\n✓ Direct agreement detected - skipping arbiter")
                    print(f"  Chosen Answer: {arbiter_result['chosen_answer']}")
            else:
                # No direct agreement - let arbiter LLM evaluate semantic similarity
                if verbose:
                    print("\nConsulting Arbiter (evaluating semantic similarity)...")
                
                try:
                    arbiter_result = self.arbiter.evaluate(current_problem, solver_results)
                    arbiter_success = True
                    
                    if verbose:
                        print(f"Arbiter Decision:")
                        print(f"  Agreement: {arbiter_result['agreement']}")
                        print(f"  Chosen Answer: {arbiter_result['chosen_answer']}")
                        print(f"  Needs Rephrase: {arbiter_result['needs_rephrase']}")
                except Exception as e:
                    if verbose:
                        print(f"Arbiter evaluation failed: {e}")
                    arbiter_success = False
                    # Use first answer as fallback
                    arbiter_result = {
                        "agreement": False,
                        "chosen_answer": answers[0] if answers else "",
                        "needs_rephrase": False,
                        "rephrased_question": ""
                    }
                    if verbose:
                        print(f"  Using fallback answer: {arbiter_result['chosen_answer']}")
            
            # Store iteration history
            history.append({
                'iteration': iteration,
                'problem': current_problem,
                'solver_results': solver_results,
                'arbiter_result': arbiter_result,
                'direct_agreement': direct_agreement,
                'arbiter_success': arbiter_success
            })
            
            # If agreement achieved, return result
            if arbiter_result['agreement']:
                if verbose:
                    print(f"\n✓ Agreement achieved after {iteration} iteration(s)!")
                
                return {
                    'final_answer': arbiter_result['chosen_answer'],
                    'agreement': True,
                    'iterations': iteration,
                    'history': history,
                    'solver_answers': answers
                }
            
            # If rephrasing is needed and provided
            if arbiter_result['needs_rephrase'] and arbiter_result['rephrased_question']:
                if verbose:
                    print(f"\nRephrasing question...")
                    print(f"New question: {arbiter_result['rephrased_question']}")
                
                current_problem = arbiter_result['rephrased_question']
                continue
            
            # No agreement and no rephrasing - return best answer
            if verbose:
                print(f"\nNo agreement after {iteration} iteration(s). Returning best answer.")
            
            return {
                'final_answer': arbiter_result['chosen_answer'],
                'agreement': False,
                'iterations': iteration,
                'history': history,
                'solver_answers': answers
            }
        
        # Max iterations reached
        if verbose:
            print(f"\nMaximum iterations ({self.max_iterations}) reached.")
        
        last_arbiter_result = history[-1]['arbiter_result'] if history else {}
        
        return {
            'final_answer': last_arbiter_result.get('chosen_answer', ''),
            'agreement': False,
            'iterations': self.max_iterations,
            'history': history,
            'solver_answers': answers if 'answers' in locals() else []
        }


class UEFParser:
    """Parser for Unified Exam Format (UEF) JSON files using Pydantic models."""
    
    def __init__(self):
        """Initialize UEF parser with Pydantic model validation."""
        pass
    
    def load_exam(self, exam_path: str, validate: bool = True) -> Union[Exam, Dict[str, Any]]:
        """
        Load and validate an exam file in UEF format.
        
        Args:
            exam_path: Path to the exam JSON file
            validate: Whether to validate using Pydantic models (default: True)
        
        Returns:
            Exam Pydantic model instance
        
        Raises:
            FileNotFoundError: If exam file doesn't exist
            ValidationError: If exam data doesn't match UEF schema
            ValueError: If exam data is invalid
        """
        exam_file = Path(exam_path)
        if not exam_file.exists():
            raise FileNotFoundError(f"Exam file not found: {exam_path}")
        
        try:
            with open(exam_file, 'r', encoding='utf-8') as f:
                exam_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in exam file: {e}")
        
        # Support backward compatibility with old 'exercises' format
        if 'exercises' in exam_data and 'exam_content' not in exam_data:
            logger.warning("Found old 'exercises' format, converting to 'exam_content.problems'")
            try:
                exam_data = self._convert_old_format(exam_data)
            except ValueError as e:
                raise ValueError(f"Failed to convert old format: {e}")
        
        if validate:
            try:
                exam = Exam(**exam_data)
                logger.info(f"Successfully loaded and validated exam: {exam.exam_title}")
                return exam
            except ValidationError as e:
                logger.error(f"Validation error: {e}")
                raise ValueError(f"Exam data doesn't match UEF schema: {e}")
        else:
            # Return as dict if validation is disabled (for backward compatibility)
            logger.warning("Validation disabled - returning raw dict instead of Exam model")
            return exam_data
    
    def _convert_old_format(self, exam_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert old 'exercises' format to new 'exam_content.problems' format.
        
        Args:
            exam_data: Exam data with old 'exercises' structure
        
        Returns:
            Exam data with new 'exam_content.problems' structure
        
        Raises:
            ValueError: If conversion fails or data is invalid
        """
        # Add required fields with defaults if missing
        if 'exam_title' not in exam_data:
            exam_data['exam_title'] = "Untitled Exam"
        if 'examiner' not in exam_data:
            exam_data['examiner'] = "Unknown"
        if 'module' not in exam_data:
            exam_data['module'] = "Unknown"
        if 'start_time' not in exam_data:
            exam_data['start_time'] = "2025-01-01 00:00"
        if 'end_time' not in exam_data:
            exam_data['end_time'] = "2025-01-01 23:59"
        if 'exam_chair' not in exam_data:
            exam_data['exam_chair'] = "Unknown"
        
        # Convert exercises to exam_content.problems
        if 'exercises' in exam_data:
            problems = exam_data.pop('exercises')
            if not isinstance(problems, list):
                raise ValueError(f"Expected 'exercises' to be a list, got {type(problems)}")
            exam_data['exam_content'] = {'problems': problems}
        else:
            raise ValueError("Cannot convert: 'exercises' field not found in exam data")
        
        return exam_data
    
    def save_exam_with_answers(self, exam: Exam, output_path: str):
        """
        Save exam data with answers filled in.
        
        Args:
            exam: Exam Pydantic model instance (with answers filled in)
            output_path: Path to save the output JSON file
        """
        # Convert Pydantic model to dict and then to JSON
        exam_dict = exam.model_dump(mode='json', exclude_none=False)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(exam_dict, f, indent=2, ensure_ascii=False)
    
    def extract_questions(self, exam: Exam) -> List[Dict[str, Any]]:
        """
        Extract all sub-questions from an exam.
        
        Note: MultipleChoiceExamQuestion types are skipped as they have predefined
        correct answers and don't require solving by the ensemble system.
        
        Args:
            exam: Exam Pydantic model instance
        
        Returns:
            List of question dicts with problem_index, sub_question_index, and question_text_latex
        """
        questions = []
        skipped_mc_count = 0
        
        for prob_idx, problem in enumerate(exam.exam_content.problems):
            if isinstance(problem, ExamQuestion):
                # Process regular exam questions
                if not problem.sub_questions:
                    logger.warning(f"ExamQuestion at index {prob_idx} has no sub-questions, skipping")
                    continue
                    
                for sq_idx, sub_question in enumerate(problem.sub_questions):
                    if not sub_question.question_text_latex:
                        logger.warning(f"Skipping empty sub-question at problem {prob_idx}, sub-question {sq_idx}")
                        continue
                        
                    questions.append({
                        'problem_index': prob_idx,
                        'sub_question_index': sq_idx,
                        'question_text_latex': sub_question.question_text_latex,
                        'available_points': sub_question.available_points,
                        'problem_total_points': problem.total_points,
                        'problem_title': problem.question_title,
                        'problem_description_latex': problem.question_description_latex,
                        'question_type': 'ExamQuestion'
                    })
            elif isinstance(problem, MultipleChoiceExamQuestion):
                # Skip multiple choice questions - they have predefined correct answers
                skipped_mc_count += len(problem.sub_questions)
                logger.info(f"Skipping MultipleChoiceExamQuestion at problem index {prob_idx} "
                           f"({len(problem.sub_questions)} sub-questions) - MC questions have predefined answers")
            else:
                logger.warning(f"Unknown problem type at index {prob_idx}: {type(problem).__name__}. "
                             f"Expected ExamQuestion or MultipleChoiceExamQuestion")
        
        if skipped_mc_count > 0:
            logger.info(f"Skipped {skipped_mc_count} multiple choice sub-questions (have predefined answers)")
        
        return questions


class ExamProcessor:
    """Processes exams in UEF format using the ensemble solver."""
    
    def __init__(self, coordinator: EnsembleCoordinator, uef_parser: UEFParser):
        """
        Initialize exam processor.
        
        Args:
            coordinator: EnsembleCoordinator instance
            uef_parser: UEFParser instance
        """
        self.coordinator = coordinator
        self.parser = uef_parser
    
    def process_exam(self, exam_path: str, output_path: Optional[str] = None, verbose: bool = True) -> Exam:
        """
        Process an entire exam file, solving all questions.
        
        Args:
            exam_path: Path to input exam JSON file
            output_path: Path to save output (if None, auto-generates from input)
            verbose: Whether to print progress
        
        Returns:
            Exam Pydantic model with answers filled in
        """
        # Load exam
        if verbose:
            print(f"Loading exam from: {exam_path}")
        
        exam = self.parser.load_exam(exam_path, validate=True)
        
        # Extract all questions (skips MultipleChoiceExamQuestion automatically)
        questions = self.parser.extract_questions(exam)
        
        # Count question types for reporting
        num_problems = len(exam.exam_content.problems)
        mc_problems = sum(1 for p in exam.exam_content.problems if isinstance(p, MultipleChoiceExamQuestion))
        regular_problems = num_problems - mc_problems
        
        # Validate that we have questions to process
        if not questions:
            error_msg = "No questions found to process. "
            if mc_problems > 0 and regular_problems == 0:
                error_msg += "Exam contains only MultipleChoiceExamQuestion types, which are skipped."
            else:
                error_msg += "Please check that the exam contains ExamQuestion types with sub-questions."
            raise ValueError(error_msg)
        
        if verbose:
            print(f"Found {len(questions)} sub-questions to process across {regular_problems} regular problems")
            if mc_problems > 0:
                print(f"Note: {mc_problems} multiple choice problem(s) skipped (have predefined answers)")
            print(f"Total points: {exam.total_points}")
            print(f"Time limit: {exam.total_time_min} minutes")
            print(f"Exam: {exam.exam_title}")
            print(f"Module: {exam.module}\n")
        
        # Process each question
        results_summary = {
            'total_questions': len(questions),
            'agreed_answers': 0,
            'disagreed_answers': 0,
            'question_results': []
        }
        
        for q_idx, question_info in enumerate(questions, 1):
            if verbose:
                print(f"\n{'#'*60}")
                print(f"Processing Question {q_idx}/{len(questions)}")
                print(f"Problem {question_info['problem_index'] + 1}, "
                      f"Sub-question {question_info['sub_question_index'] + 1}")
                if question_info.get('problem_title'):
                    print(f"Title: {question_info['problem_title']}")
                print(f"Points: {question_info['available_points']}")
                print(f"{'#'*60}")
            
            question_text = question_info['question_text_latex']
            
            # Solve using ensemble (UEF questions are in LaTeX format)
            result = self.coordinator.solve(question_text, verbose=verbose, is_latex=True)
            
            # Store answer in exam model
            prob_idx = question_info['problem_index']
            sq_idx = question_info['sub_question_index']
            
            # Update the answer in the exam structure
            problem = exam.exam_content.problems[prob_idx]
            if isinstance(problem, ExamQuestion):
                # Update the answer for regular exam questions
                problem.sub_questions[sq_idx].question_answer_latex = result['final_answer']
                
                # Store metadata in a dict format (Pydantic models don't support arbitrary fields)
                # We'll store it as a JSON string in a comment or separate metadata file
                # For now, we'll add it to the model dict after conversion
                # Note: This requires converting to dict, adding metadata, then back to model
                # For simplicity, we'll store metadata separately or in a custom field
            elif isinstance(problem, MultipleChoiceExamQuestion):
                # This shouldn't happen as extract_questions() skips MC questions
                logger.warning(f"Attempted to process MultipleChoiceExamQuestion at index {prob_idx} - skipping")
                continue
            else:
                logger.error(f"Unknown problem type at index {prob_idx}: {type(problem)}")
                continue
            
            # Update summary
            if result['agreement']:
                results_summary['agreed_answers'] += 1
            else:
                results_summary['disagreed_answers'] += 1
            
            results_summary['question_results'].append({
                'question_index': q_idx,
                'problem_index': prob_idx,
                'sub_question_index': sq_idx,
                'agreement': result['agreement'],
                'iterations': result['iterations']
            })
        
        # Save output
        if output_path is None:
            input_path = Path(exam_path)
            output_path = str(input_path.parent / f"{input_path.stem}_solved{input_path.suffix}")
        
        if verbose:
            print(f"\n{'='*60}")
            print("Saving results...")
        
        self.parser.save_exam_with_answers(exam, output_path)
        
        if verbose:
            print(f"Saved to: {output_path}")
            print(f"\n{'='*60}")
            print("PROCESSING SUMMARY")
            print(f"{'='*60}")
            print(f"Total questions: {results_summary['total_questions']}")
            print(f"Agreed answers: {results_summary['agreed_answers']}")
            print(f"Disagreed answers: {results_summary['disagreed_answers']}")
            if results_summary['total_questions'] > 0:
                agreement_rate = results_summary['agreed_answers'] / results_summary['total_questions'] * 100
                print(f"Agreement rate: {agreement_rate:.1f}%")
        
        return exam


def main() -> None:
    """Example usage of the ensemble system."""
    import sys
    
    coordinator = EnsembleCoordinator(max_iterations=3)
    uef_parser = UEFParser()
    
    # Check if exam file is provided as argument
    if len(sys.argv) > 1:
        exam_path = sys.argv[1]
        if Path(exam_path).exists():
            print(f"Processing exam file: {exam_path}")
            processor = ExamProcessor(coordinator, uef_parser)
            processor.process_exam(exam_path, verbose=True)
            return
        else:
            print(f"Error: Exam file not found: {exam_path}")
            return
    
    # Otherwise, use interactive mode for single problem
    print("No exam file provided. Running in interactive mode.")
    print("Usage: python ensemble_solver.py <exam_file.json>")
    print("\n" + "="*60)
    
    problem = input("Enter a math problem: ").strip()
    
    if not problem:
        problem = "Solve for x: 2x + 5 = 13"
        print(f"Using example problem: {problem}")
    
    result = coordinator.solve(problem, verbose=True)
    
    print(f"\n{'='*60}")
    print("FINAL RESULT")
    print(f"{'='*60}")
    print(f"Final Answer: {result['final_answer']}")
    print(f"Agreement: {result['agreement']}")
    print(f"Iterations: {result['iterations']}")
    print(f"\nSolver Answers:")
    for i, answer in enumerate(result['solver_answers'], 1):
        print(f"  Solver {i}: {answer}")


if __name__ == "__main__":
    main()

