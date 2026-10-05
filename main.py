"""FastAPI backend for Resume AI Assistant."""

import logging
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

from config import settings
from services.gemini_service import GeminiServiceError, generate_resume_response
from services.resume_parser import ResumeParserError, extract_resume_text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

MAX_QUESTION_CHARS = 2000

app = FastAPI(title="Resume AI Assistant")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/config")
def get_config() -> dict:
    """Lets the frontend know the upload limits."""
    return {
        "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
        "supported_extensions": list(settings.SUPPORTED_EXTENSIONS),
    }


# Plain `def` (not async): FastAPI runs it in a worker thread,
# so the slow Gemini call does not block other requests.
@app.post("/api/ask")
def ask(file: UploadFile = File(...), question: str = Form(...)) -> dict:
    question = question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Please enter a question about your resume.")
    if len(question) > MAX_QUESTION_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"Your question is too long. Please keep it under {MAX_QUESTION_CHARS} characters.",
        )

    # Read at most limit + 1 bytes so a huge file cannot fill memory.
    file_bytes = file.file.read(settings.MAX_FILE_SIZE_BYTES + 1)
    if len(file_bytes) > settings.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File is too large. Please upload a file smaller than {settings.MAX_FILE_SIZE_MB} MB.",
        )

    try:
        resume_text = extract_resume_text(file.filename or "", file_bytes)
        answer = generate_resume_response(resume_text, question)
    except ResumeParserError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GeminiServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error")
        raise HTTPException(
            status_code=500, detail="Something went wrong. Please try again."
        ) from exc

    return {
        "answer": answer,
        "truncated": len(resume_text) > settings.MAX_RESUME_CHARS,
    }


# Serve the built React app (only exists inside the Docker image).
# This must stay LAST so it does not shadow the /api routes.
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")