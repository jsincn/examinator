import os
import sys
import base64
import fitz  # PyMuPDF
from dotenv import load_dotenv
from openai import OpenAI

from inodatamodel import Exam, ExamContent, ExamMetadataOnly

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def encode_page(page):
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    return base64.b64encode(pix.tobytes("png")).decode("utf-8")

#Metadata
def parse_metadata(doc):
    print("[Step 1] Analysiere Deckblatt (Metadaten)...")
    
    #nur die erste seite
    first_page_img = encode_page(doc[0])
    
    completion = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "Extract exam metadata from the cover page. Look for Examiner, Module Name, Time, and Total Points."
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract metadata."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{first_page_img}", "detail": "high"}}
                ],
            }
        ],
        response_format=ExamMetadataOnly, #Hilfsmodell
    )
    return completion.choices[0].message.parsed

#CONTENT 
def parse_content(doc):
    print(f"[Step 2] Analysiere Aufgaben (Seite 2 bis {len(doc)})...")
    
    images = []
    # Wir starten ab Seite 2 (Index 1), da Seite 1 nur Deckblatt ist
    for i in range(1, len(doc)):
        # Optional: Limit für Tests 
        # if i > 5: break 
        
        print(f"   - Verarbeite Seite {i+1}")
        b64 = encode_page(doc[i])
        images.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"}
        })

    completion = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert exam parser. Extract all problems into the structure.\n"
                    "IMPORTANT:\n"
                    "- Distinguish between 'ExamQuestion' (Text/Math) and 'MultipleChoiceExamQuestion' (Checkbox/Options).\n"
                    "- For MC: Extract options and correct indices if marked.\n"
                    "- Use LaTeX for all math."
                )
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract the exam problems."},
                    *images
                ],
            }
        ],
        response_format=ExamContent, # Content teil
    )
    return completion.choices[0].message.parsed

#merge beide 
def parse_exam_complete(pdf_path):
    if not os.path.exists(pdf_path):
        raise FileNotFoundError("PDF nicht gefunden")

    doc = fitz.open(pdf_path)
    
    # metadata 
    meta = parse_metadata(doc)
    print(f"Metadaten erkannt: {meta.exam_title} ({meta.examiner})")
    
    #content
    content = parse_content(doc)
    print(f" Content erkannt: {len(content.problems)} Aufgaben")
    
    # zusammenfügen
    final_exam = Exam(
        total_points=meta.total_points,
        total_time_min=meta.total_time_min,
        exam_title=meta.exam_title,
        examiner=meta.examiner,
        module=meta.module,
        start_time=meta.start_time,
        end_time=meta.end_time,
        exam_chair=meta.exam_chair,
        exam_content=content 
    )
    
    return final_exam

if __name__ == "__main__":
    
    pdf_file = sys.argv[1] if len(sys.argv) > 1 else "TUMIntrotoDL.pdf"
    output_file = pdf_file.replace(".pdf", ".json")

    try:
        result = parse_exam_complete(pdf_file)
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))
            
        print(f"SUCCESS! Finales JSON: {output_file}")
        
    except Exception as e:
        print(f"ERROR: {e}")