from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from openai import OpenAI

app = Flask(__name__)
CORS(app)
@app.route("/")
def home():
    return send_from_directory(".", "index.html")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
import pdfplumber

@app.route("/analyze", methods=["POST"])
def analyze():
    question = request.json.get("question", "")

    combined_text = ""

    objects = s3.list_objects_v2(Bucket=BUCKET)

    if "Contents" in objects:
        for obj in objects["Contents"]:
            try:
                file_obj = s3.get_object(Bucket=BUCKET, Key=obj["Key"])
                
                # Save temp file
                file_path = f"/tmp/{obj['Key']}"
                with open(file_path, "wb") as f:
                    f.write(file_obj["Body"].read())

                # Extract text from PDF
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            combined_text += text + "\n\n"print(text[:500])

            except:
                continue

    prompt = f"""
    You are analyzing engineering test reports.

    Extract and answer clearly.

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
