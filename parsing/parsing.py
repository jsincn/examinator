import os
import sys  
import base64
import fitz  # PyMuPDF  
from dotenv import load_dotenv
from openai import OpenAI
from models import Exam 

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("API KEY NICHT GEFUNDEN")
    sys.exit(1)

client = OpenAI(api_key=api_key)

def encode_page(page):
    """Konvertiert eine PDF-Seite in ein Base64-Bild (High-Res)."""
    # Matrix(2, 2) verdoppelt die Auflösung 
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    return base64.b64encode(pix.tobytes("png")).decode("utf-8")

def parse_exam(pdf_path):
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Die Datei '{pdf_path}' existiert nicht!")

    print(f"Starte Parsing für: {pdf_path}")
    doc = fitz.open(pdf_path)
    
    images = []
    
    print(f"Verarbeite {len(doc)} Seiten...")
    
    for i, page in enumerate(doc):
        # if i > 4: break 
        
        b64 = encode_page(page)
        images.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"}
        })

    print(f"Sende Daten an LLM")
    
    completion = client.beta.chat.completions.parse(
        model="gpt-4o", 
        messages=[
            {
                "role": "system", 
                "content": "You are an exam parser. Extract the exam structure exactly into the JSON format. Use LaTeX for math. Extract the 'title' of problems if visible (e.g. 'Problem 1: Logic')."
            },
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": "Parse this exam document."},
                    *images
                ],
            }
        ],
        response_format=Exam,
    )

    return completion.choices[0].message.parsed


if __name__ == "__main__":
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]  # Erlaubt auch Pfade
    else:
        print("Kein Dateiname angegeben nutzen standart")
        pdf_file = "TUMIntrotoDL.pdf"   

    output_file = pdf_file.replace(".pdf", ".json")

    try:
        result = parse_exam(pdf_file)
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))
            
        print(f"LESGOOOOO! Ergebnis gespeichert in: '{output_file}'")
        
    except Exception as e:
        print(f" Error: {e}")