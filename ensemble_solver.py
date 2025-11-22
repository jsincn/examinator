"""
Math-Solver Ensemble System
Coordinates three independent Solver LLMs and an Arbiter LLM
to solve math problems with agreement checking and rephrasing.
Supports Unified Exam Format (UEF) for structured exam processing.
"""

import os
import json
import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

class Solver:
    """Independent Solver LLM that attempts to solve math problems."""
    
    def __init__(self, model: str, name: str):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = model
        self.name = name
    
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
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a math-specialist model. Provide clear, concise solutions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3  # Lower temperature for more consistent results
            )
            
            full_response = response.choices[0].message.content.strip()
            
            # Extract final answer
            answer_match = re.search(r'Final Answer:\s*(.+)', full_response, re.IGNORECASE)
            if answer_match:
                answer = answer_match.group(1).strip()
            else:
                # Try to extract the last line as answer
                lines = full_response.split('\n')
                answer = lines[-1].strip() if lines else full_response
            
            return answer, full_response
            
        except Exception as e:
            print(f"Error in {self.name}: {e}")
            return "ERROR", f"Error occurred: {str(e)}"


class Arbiter:
    """Arbiter LLM that evaluates solver agreement and correctness."""
    
    def __init__(self, model: str):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = model
    
    def evaluate(self, problem: str, solver_results: List[Dict[str, str]]) -> Dict:
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
        
        prompt = f"""Compare the three solver outputs below.

Decide if they match.

If they match → provide final answer.
If not → choose the most plausible answer OR request a rephrasing.

Return your decision in JSON format. Start your response with {{ and end with }}:

{{
  "agreement": true/false,
  "chosen_answer": "...",
  "needs_rephrase": true/false,
  "rephrased_question": "..."
}}

Rules:
- Set "agreement" to true only if all three answers are essentially the same (allowing for minor formatting differences)
- If agreement is false, set "chosen_answer" to the most plausible answer
- Set "needs_rephrase" to true only if the question is ambiguous and rephrasing would help
- If rephrasing, "rephrased_question" must preserve ALL numbers, variables, and mathematical relationships
- Do NOT change any mathematical content, only clarify wording

Original Problem:
{problem}

Solver Results:
{results_text}"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an arbiter that evaluates math solutions. You must respond with valid JSON only, starting with { and ending with }."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            
            response_text = response.choices[0].message.content.strip()
            
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
        """Normalize answer for comparison (remove whitespace, convert to lowercase)."""
        # Remove LaTeX dollar signs
        normalized = answer.replace('$', '')
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized.strip())
        # Normalize commas and spacing around them
        normalized = re.sub(r'\s*,\s*', ',', normalized)
        # Normalize equals signs and spacing
        normalized = re.sub(r'\s*=\s*', '=', normalized)
        # Convert to lowercase for comparison
        normalized = normalized.lower()
        # Remove backslashes (LaTeX commands) but keep the content
        normalized = normalized.replace('\\', '')
        return normalized
    
    def answers_match(self, answers: List[str]) -> bool:
        """Check if all answers are essentially the same."""
        if len(answers) < 2:
            return True
        
        normalized = [self.normalize_answer(a) for a in answers]
        
        # Check if all normalized answers are the same
        return all(n == normalized[0] for n in normalized)
    
    def solve(self, problem: str, verbose: bool = True, is_latex: bool = None) -> Dict:
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
            
            # Check for direct agreement
            answers = [r['answer'] for r in solver_results]
            direct_agreement = self.answers_match(answers)
            
            if verbose:
                print(f"\nDirect Agreement Check: {direct_agreement}")
            
            # Send to arbiter for evaluation
            if verbose:
                print("\nConsulting Arbiter...")
            
            try:
                arbiter_result = self.arbiter.evaluate(current_problem, solver_results)
                arbiter_success = True
            except Exception as e:
                if verbose:
                    print(f"Arbiter evaluation failed: {e}")
                arbiter_success = False
                # Use direct agreement check as fallback
                arbiter_result = {
                    "agreement": direct_agreement,
                    "chosen_answer": answers[0] if answers else "",
                    "needs_rephrase": False,
                    "rephrased_question": ""
                }
            
            if verbose:
                print(f"Arbiter Decision:")
                print(f"  Agreement: {arbiter_result['agreement']}")
                print(f"  Chosen Answer: {arbiter_result['chosen_answer']}")
                print(f"  Needs Rephrase: {arbiter_result['needs_rephrase']}")
            
            # If direct agreement was detected, use that (more reliable than arbiter)
            if direct_agreement:
                arbiter_result['agreement'] = True
                # Use the most common answer or first answer
                arbiter_result['chosen_answer'] = answers[0]
            
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
    """Parser for Unified Exam Format (UEF) JSON files."""
    
    def __init__(self, uef_schema_path: str = "uef.json"):
        """
        Initialize UEF parser with schema validation.
        
        Args:
            uef_schema_path: Path to the UEF schema JSON file
        """
        self.schema_path = Path(uef_schema_path)
        self.schema = None
        if self.schema_path.exists():
            with open(self.schema_path, 'r', encoding='utf-8') as f:
                self.schema = json.load(f)
    
    def load_exam(self, exam_path: str) -> Dict:
        """
        Load and validate an exam file in UEF format.
        
        Args:
            exam_path: Path to the exam JSON file
        
        Returns:
            Dict containing the exam data
        """
        exam_file = Path(exam_path)
        if not exam_file.exists():
            raise FileNotFoundError(f"Exam file not found: {exam_path}")
        
        with open(exam_file, 'r', encoding='utf-8') as f:
            exam_data = json.load(f)
        
        # Basic validation
        required_fields = ['total_points', 'total_time_min', 'exercises']
        for field in required_fields:
            if field not in exam_data:
                raise ValueError(f"Missing required field: {field}")
        
        return exam_data
    
    def save_exam_with_answers(self, exam_data: Dict, output_path: str):
        """
        Save exam data with answers filled in.
        
        Args:
            exam_data: Exam data dictionary (modified in place with answers)
            output_path: Path to save the output JSON file
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(exam_data, f, indent=2, ensure_ascii=False)
    
    def extract_questions(self, exam_data: Dict) -> List[Dict]:
        """
        Extract all sub-questions from an exam.
        
        Returns:
            List of question dicts with exercise_index, sub_question_index, and question_text_latex
        """
        questions = []
        for ex_idx, exercise in enumerate(exam_data.get('exercises', [])):
            for sq_idx, sub_question in enumerate(exercise.get('sub_questions', [])):
                questions.append({
                    'exercise_index': ex_idx,
                    'sub_question_index': sq_idx,
                    'question_text_latex': sub_question.get('question_text_latex', ''),
                    'available_points': sub_question.get('available_points', 0),
                    'exercise_total_points': exercise.get('total_points', 0)
                })
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
    
    def process_exam(self, exam_path: str, output_path: str = None, verbose: bool = True) -> Dict:
        """
        Process an entire exam file, solving all questions.
        
        Args:
            exam_path: Path to input exam JSON file
            output_path: Path to save output (if None, auto-generates from input)
            verbose: Whether to print progress
        
        Returns:
            Dict with exam data including answers
        """
        # Load exam
        if verbose:
            print(f"Loading exam from: {exam_path}")
        
        exam_data = self.parser.load_exam(exam_path)
        
        # Extract all questions
        questions = self.parser.extract_questions(exam_data)
        
        if verbose:
            print(f"Found {len(questions)} sub-questions across {len(exam_data['exercises'])} exercises")
            print(f"Total points: {exam_data['total_points']}")
            print(f"Time limit: {exam_data['total_time_min']} minutes\n")
        
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
                print(f"Exercise {question_info['exercise_index'] + 1}, "
                      f"Sub-question {question_info['sub_question_index'] + 1}")
                print(f"Points: {question_info['available_points']}")
                print(f"{'#'*60}")
            
            question_text = question_info['question_text_latex']
            
            # Solve using ensemble (UEF questions are in LaTeX format)
            result = self.coordinator.solve(question_text, verbose=verbose, is_latex=True)
            
            # Store answer in exam data
            ex_idx = question_info['exercise_index']
            sq_idx = question_info['sub_question_index']
            
            # Update the answer in the exam structure
            exam_data['exercises'][ex_idx]['sub_questions'][sq_idx]['question_answer_latex'] = result['final_answer']
            
            # Store metadata (we'll add a new field for this)
            if 'solver_metadata' not in exam_data['exercises'][ex_idx]['sub_questions'][sq_idx]:
                exam_data['exercises'][ex_idx]['sub_questions'][sq_idx]['solver_metadata'] = {}
            
            exam_data['exercises'][ex_idx]['sub_questions'][sq_idx]['solver_metadata'] = {
                'agreement': result['agreement'],
                'iterations': result['iterations'],
                'solver_answers': result['solver_answers']
            }
            
            # Update summary
            if result['agreement']:
                results_summary['agreed_answers'] += 1
            else:
                results_summary['disagreed_answers'] += 1
            
            results_summary['question_results'].append({
                'question_index': q_idx,
                'exercise_index': ex_idx,
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
        
        self.parser.save_exam_with_answers(exam_data, output_path)
        
        if verbose:
            print(f"Saved to: {output_path}")
            print(f"\n{'='*60}")
            print("PROCESSING SUMMARY")
            print(f"{'='*60}")
            print(f"Total questions: {results_summary['total_questions']}")
            print(f"Agreed answers: {results_summary['agreed_answers']}")
            print(f"Disagreed answers: {results_summary['disagreed_answers']}")
            print(f"Agreement rate: {results_summary['agreed_answers']/results_summary['total_questions']*100:.1f}%")
        
        return exam_data


def main():
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

