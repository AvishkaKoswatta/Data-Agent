from flask import Flask, render_template, request, jsonify, redirect, url_for
from scripts.main_agent import LLMBrainAgent, df, registry
from groq import Groq
import os
import boto3
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# =========================
# LLM CLIENT
# =========================
client = Groq(api_key=os.getenv("GROQ_KEY"))

agent = LLMBrainAgent(
    model_name="llama3",
    registry=registry,
    df=df,
    llm_client=client
)

# =========================
# AWS S3 CONFIG
# =========================
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name="ap-south-1"
)

# =========================
# HOME PAGE
# =========================
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


# =========================
# QUERY ENDPOINT (DATA AGENT)
# =========================
@app.route("/query", methods=["POST"])
def query():
    user_query = request.form.get("query", "").strip()

    if not user_query:
        return jsonify({"type": "error", "error": "Empty query", "code": ""})

    output = agent.handle_query(user_query)

    if not isinstance(output, dict):
        return jsonify({"type": "error", "error": str(output), "code": ""})

    response = {
        "type": output.get("type", "scalar"),
        "code": output.get("code", "")
    }

    result_type = output.get("type")

    if result_type == "error":
        response["error"] = output.get("error", "Unknown error")

    elif result_type == "chart":
        response["data"] = output.get("result", "{}")

    elif result_type == "table":
        response["columns"] = output.get("columns", [])
        response["rows"] = output.get("rows", [])

    elif result_type == "scalar":
        response["result"] = output.get("result", "")

    else:
        response["result"] = str(output.get("result", ""))

    return jsonify(response)


# =========================
# UPLOAD PAGE (UI)
# =========================
@app.route("/upload-page", methods=["GET"])
def upload_page():
    return render_template("upload.html")


# =========================
# FILE UPLOAD TO S3
# =========================
@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files.get("file")

    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    try:
        # Auto date folder
        today = datetime.now().strftime("%Y_%m_%d")

        # S3 key
        key = f"{today}/{file.filename}"

        # Upload to S3
        s3.upload_fileobj(file, BUCKET_NAME, key)

        return jsonify({
            "message": "Uploaded successfully",
            "key": key
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    app.run(debug=True)