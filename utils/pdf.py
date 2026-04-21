import io

import pdfplumber


def extract_pdf_text(file):
    file.seek(0)
    text = ""
    with pdfplumber.open(io.BytesIO(file.read())) as pdf:
        for page in pdf.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
    return text.strip()
