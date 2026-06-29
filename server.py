from flask import Flask, request, jsonify
from openai import OpenAI
from flask_cors import CORS
import fitz
import pytesseract
from PIL import Image
import io

app = Flask(__name__)
CORS(app)

# 🔑 ADD YOUR API KEY HERE
import os
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 🔧 Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"


# 📄 Extract text (with OCR fallback)
def extract_text_from_pdf(file):
    file_bytes = file.read()
    doc = fitz.open(stream=file_bytes, filetype="pdf")

    text = ""

    for page in doc:
        text += page.get_text()

    # OCR fallback
    if len(text.strip()) < 50:
        print("OCR ACTIVATED")
        text = ""
        for page in doc:
            pix = page.get_pixmap()
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text += pytesseract.image_to_string(img)

    return text


# 📥 Upload route
@app.route("/analyze", methods=["POST"])
def analyze():
    file = request.files["file"]

    try:
        text = extract_text_from_pdf(file)
        return jsonify(text)

    except Exception as e:
        return jsonify({"error": str(e)})


# 🧠 AI Analyze (ChatGPT-style)
@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_data(as_text=True)

    prompt = f"""
You are an expert engineering assistant helping a team analyze aggregate test data and specifications.

Your job is to behave like a knowledgeable human expert, not a rigid system.

GUIDELINES:

- Answer the user's question directly and clearly
- Be conversational and natural (like ChatGPT)
- Do NOT force structured formats unless the question asks for analysis
- Do NOT assume requirements unless they are explicitly stated in the documents
- If the user asks a simple question, give a simple answer
- If the user asks for analysis, then provide deeper reasoning

UNDERSTANDING:

- LA Abrasion = Los Angeles Abrasion = same test

IMPORTANT:
- Only use the provided document data
- Do NOT guess or invent standards

DOCUMENTS:
{data}

USER QUESTION:
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content

    except Exception as e:
        return str(e)


if __name__ == "__main__":
    app.run(port=5000)