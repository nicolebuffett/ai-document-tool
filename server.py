from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from openai import OpenAI
import boto3
import pdfplumber

app = Flask(__name__)
CORS(app)

# -------- HOME --------
@app.route("/")
def home():
    return send_from_directory(".", "index.html")

# -------- CONFIG --------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

textract = boto3.client(
    "textract",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name="us-east-2"
)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------- UPLOAD --------
@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"message": "No file uploaded"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"message": "No selected file"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    print("Saved to:", filepath)

    return jsonify({"message": "Upload successful"})

# -------- LIBRARY --------
@app.route("/library", methods=["GET"])
def library():
    files = os.listdir(UPLOAD_FOLDER)
    print("Library files:", files)
    return jsonify({"files": files})

# -------- DOWNLOAD --------
@app.route("/download/<filename>", methods=["GET"])
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

# -------- SEARCH --------
@app.route("/search", methods=["POST"])
def search():
    query = request.json.get("query", "").lower()
    results = []

    for filename in os.listdir(UPLOAD_FOLDER):
        try:
            file_path = os.path.join(UPLOAD_FOLDER, filename)

            text_found = ""

            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_found += text.lower()

            if query in text_found:
                results.append(filename)

        except Exception as e:
            print("SEARCH ERROR:", e)

    return jsonify({"result": results})
# -------- AI ANALYZE --------
@app.route("/analyze", methods=["POST"])
def analyze():
    question = request.json.get("question", "")
    combined_text = ""

    files = os.listdir(UPLOAD_FOLDER)

    for filename in files:
        try:
            file_path = os.path.join(UPLOAD_FOLDER, filename)

            text_found = ""

            # ---- TRY NORMAL PDF ----
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_found += text + "\n"

            # ---- OCR FALLBACK ----
            if not text_found.strip():
                print("Using OCR for:", filename)

                with open(file_path, "rb") as doc:
                    response = textract.detect_document_text(
                        Document={"Bytes": doc.read()}
                    )

                for item in response["Blocks"]:
                    if item["BlockType"] == "LINE":
                        text_found += item["Text"] + "\n"

            combined_text += text_found + "\n\n"

        except Exception as e:
            print("ERROR:", e)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": f"""
You are analyzing engineering test reports.

Extract test values clearly and directly.

Documents:
{combined_text}

Question:
{question}
"""
        }]
    )

    return jsonify({"answer": response.choices[0].message.content})

# -------- RUN --------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
