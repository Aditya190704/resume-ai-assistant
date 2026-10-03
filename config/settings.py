"""Central configuration. Values come from environment variables."""

import os

from dotenv import load_dotenv

# Reads a local .env file if present. On Cloud Run there is no .env, which is fine.
load_dotenv()

GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "").strip()
GCP_LOCATION: str = os.getenv("GCP_LOCATION", "asia-south1").strip()
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

# Thinking effort: minimal, low, medium or high
_VALID_THINKING_LEVELS = {"minimal", "low", "medium", "high"}
_thinking = os.getenv("THINKING_LEVEL", "medium").strip().lower()
THINKING_LEVEL: str = _thinking if _thinking in _VALID_THINKING_LEVELS else "medium"

MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024

SUPPORTED_EXTENSIONS: tuple[str, ...] = (".pdf", ".docx", ".txt")

# Safety limits for very large resumes / long answers
MAX_RESUME_CHARS: int = int(os.getenv("MAX_RESUME_CHARS", "60000"))
MAX_OUTPUT_TOKENS: int = int(os.getenv("MAX_OUTPUT_TOKENS", "8192"))

