"""Extract text from PDF files."""

from PyPDF2 import PdfReader
from typing import List
from extract.epub_extractor import Chapter


def extract_text_from_pdf(pdf_path: str) -> List[Chapter]:
    """
    Extract text from PDF file.

    Note: Basic PDF extraction without OCR.
    Chapter detection is minimal - treats each page as potential content.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        List of Chapter objects (currently just one chapter with all text)
    """
    reader = PdfReader(pdf_path)

    # Extract all text
    all_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text.strip():
            all_text.append(text)

    full_text = "\n\n".join(all_text)

    # For now, treat entire PDF as one chapter
    # TODO: Implement better chapter detection
    return [Chapter(title="PDF Book", text=full_text)]
