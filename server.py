from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from openai import OpenAI
import boto3

app = Flask(__name__)
CORS(app)
@app.route("/")
def home():
    return send_from_directory(".", "index.html")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
textract = boto3.client(
    "textract",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name="us-east-2"
)
s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)

BUCKET = os.getenv("S3_BUCKET_NAME")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------- UPLOAD --------
@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"message": "No file uploaded"}), 400

    file = request.files["file"]
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    return jsonify({"message": "Upload successful"})

# -------- LIBRARY --------
@app.route("/library", methods=["GET"])
def library():
    files = os.listdir(UPLOAD_FOLDER)
    return jsonify({"files": files})

# -------- DOWNLOAD --------
@app.route("/download/<filename>", methods=["GET"])
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

# -------- SEARCH --------
@app.route("/search", methods=["POST"])
def search():
    query = request.json.get("query", "").lower()
    matches = []

    for file in os.listdir(UPLOAD_FOLDER):
        if query in file.lower():
            matches.append(file)

    return jsonify({"result": matches})

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
            continue

    prompt = f"""
    You are analyzing engineering test reports.

    Extract test values clearly and directly.

    Documents:
    {combined_text}

    Question:
    {question}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return jsonify({"answer": response.choices[0].message.content})

# -------- RUN --------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
