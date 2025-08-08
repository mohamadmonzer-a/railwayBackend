from fastapi import FastAPI, UploadFile, File, HTTPException
from supabase import create_client, Client
import openai
import os
from pypdf import PdfReader
import hashlib
import logging
import time

app = FastAPI()

# Load environment variables (optional if you use os.environ directly)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-3-small")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not (OPENAI_API_KEY and SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY):
    raise Exception("Missing environment variables for OpenAI or Supabase")

openai.api_key = OPENAI_API_KEY
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(file_bytes)
    text = ""
    for page in reader.pages:
        text_page = page.extract_text()
        if text_page:
            text += text_page + "\n"
    return text.strip()

def get_embedding(text: str):
    response = openai.Embedding.create(
        input=text,
        model=EMBEDDING_MODEL_NAME
    )
    return response['data'][0]['embedding']

def hash_content(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

@app.post("/upload_pdf/")
async def upload_pdf(file: UploadFile = File(...), session_id: str = None):
    start_time = time.time()
    try:
        if not file.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

        content_bytes = await file.read()
        logging.info(f"Read file in {time.time() - start_time:.2f}s")

        text = extract_text_from_pdf(content_bytes)
        logging.info(f"Extracted text length={len(text)} in {time.time() - start_time:.2f}s")

        content_hash = hash_content(text)

        # Check if content_hash already exists
        existing = supabase.from_("pdf").select("id").eq("content_hash", content_hash).execute()
        if existing.data and len(existing.data) > 0:
            return {"message": "This PDF content already exists in the database."}

        embedding_vector = get_embedding(text)
        logging.info(f"Got embedding in {time.time() - start_time:.2f}s")

        insert_data = {
            "session_id": session_id or "default",
            "content": text,
            "content_hash": content_hash,
            "message": None,
            "embedding": embedding_vector,
            "metadata": {},
            "file_name": file.filename
        }

        result = supabase.from_("pdf").insert(insert_data).execute()
        if result.error:
            raise HTTPException(status_code=500, detail=f"Supabase insert error: {result.error.message}")

        logging.info(f"Inserted to DB in {time.time() - start_time:.2f}s")
        return {"message": "PDF uploaded and embedded successfully.", "id": result.data[0]["id"]}

    except Exception as e:
        logging.error(f"Error in upload_pdf: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
