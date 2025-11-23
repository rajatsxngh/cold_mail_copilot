# src/pdf_utils.py
from pypdf import PdfReader

def extract_text_from_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)
    texts = []
    for page in reader.pages:
        texts.append(page.extract_text() or "")
    return "\n".join(texts)