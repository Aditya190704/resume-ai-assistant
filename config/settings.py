# This file keeps all important application settings in one place.
"""Central configuration. Values come from environment variables."""

# This module helps us read operating-system environment variables.
import os

# This function loads values from a local .env file.
from dotenv import load_dotenv


# This loads the .env file if it exists on the local computer.
# On Cloud Run, environment variables are provided directly, so .env is not required.
load_dotenv()


# Get the Google Cloud project ID from the environment variable.
# If it is not found, use an empty string as the default value.
GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "").strip()


# Get the Google Cloud location from the environment variable.
# If it is not provided, use asia-south1 as the default location.
GCP_LOCATION: str = os.getenv("GCP_LOCATION", "asia-south1").strip()


# Get the Gemini model name from the environment variable.
# If it is not provided, use gemini-2.5-flash as the default model.
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()


# These are the only thinking levels that the application allows.
_VALID_THINKING_LEVELS = {"minimal", "low", "medium", "high"}


# Read the thinking level from the environment variable.
# If it is not provided, use medium as the default level.
_thinking = os.getenv("THINKING_LEVEL", "medium").strip().lower()


# Use the given thinking level only if it is valid; otherwise use medium.
THINKING_LEVEL: str = _thinking if _thinking in _VALID_THINKING_LEVELS else "medium"


# Get the maximum allowed resume file size in megabytes.
# If it is not provided, allow files up to 10 MB.
MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))


# Convert the maximum file size from megabytes to bytes.
MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024


# These are the file types that the application allows users to upload.
SUPPORTED_EXTENSIONS: tuple[str, ...] = (".pdf", ".docx", ".txt")


# Set the maximum number of characters that can be processed from a resume.
# This prevents very large resumes from using too many resources.
MAX_RESUME_CHARS: int = int(os.getenv("MAX_RESUME_CHARS", "60000"))


# Set the maximum number of tokens that Gemini can generate in its response.
# This helps control the response length and resource usage.
MAX_OUTPUT_TOKENS: int = int(os.getenv("MAX_OUTPUT_TOKENS", "8192"))
