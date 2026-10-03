"""All Gemini / Vertex AI communication lives in this file."""

import logging
from functools import lru_cache

from google import genai
from google.auth.exceptions import GoogleAuthError
from google.genai import errors, types

from config import settings
from prompts.resume_prompt import build_resume_prompt

logger = logging.getLogger(__name__)


class GeminiServiceError(Exception):
    """Raised with a user-friendly message when Gemini cannot answer."""


@lru_cache(maxsize=1)
def _get_client() -> genai.Client:
    """Create the Vertex AI client once. Uses Application Default Credentials."""
    return genai.Client(
        vertexai=True,
        project=settings.GCP_PROJECT_ID,
        location=settings.GCP_LOCATION,
    )


def _build_config() -> types.GenerateContentConfig:
    config_args = {"max_output_tokens": settings.MAX_OUTPUT_TOKENS}

    # thinking_level sirf Gemini 3 models ke liye hai.
    # Gemini 2.5 mein hum thinking ka koi setting nahi bhejte (default use hoga).
    if settings.GEMINI_MODEL.startswith("gemini-3"):
        thinking_level = getattr(types.ThinkingLevel, settings.THINKING_LEVEL.upper())
        config_args["thinking_config"] = types.ThinkingConfig(thinking_level=thinking_level)

    return types.GenerateContentConfig(**config_args)


def _limit_resume_length(resume_text: str) -> str:
    if len(resume_text) > settings.MAX_RESUME_CHARS:
        logger.warning("Resume text truncated to %d characters", settings.MAX_RESUME_CHARS)
        return resume_text[: settings.MAX_RESUME_CHARS]
    return resume_text


def _api_error_message(exc: errors.APIError) -> str:
    code = getattr(exc, "code", None)
    if code in (401, 403):
        return (
            "Authentication failed. Please check your Google Cloud credentials, "
            "IAM role (Vertex AI User) and that the Vertex AI API is enabled."
        )
    if code == 404:
        return (
            "Model or location not found. Please check GEMINI_MODEL and GCP_LOCATION."
        )
    if code == 429:
        return "Too many requests or quota exceeded. Please wait a moment and try again."
    if code is not None and code >= 500:
        return "Vertex AI is temporarily unavailable. Please try again shortly."
    return "Gemini could not process this request. Please try again."


def generate_resume_response(resume_text: str, user_question: str) -> str:
    """Send resume + question to Gemini and return the answer text."""
    if not settings.GCP_PROJECT_ID:
        raise GeminiServiceError(
            "GCP_PROJECT_ID is not set. Please add it to your .env file."
        )

    prompt = build_resume_prompt(_limit_resume_length(resume_text), user_question)

    try:
        response = _get_client().models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=_build_config(),
        )
    except GoogleAuthError as exc:
        logger.error("Google auth error: %s", type(exc).__name__)
        raise GeminiServiceError(
            "Authentication failed. Please check your Google Cloud credentials."
        ) from exc
    except errors.APIError as exc:
        logger.error("Vertex AI API error: code=%s", getattr(exc, "code", None))
        raise GeminiServiceError(_api_error_message(exc)) from exc

    except Exception as exc:
        error_name = type(exc).__name__
        if any(word in error_name for word in ("Connect", "Timeout", "Transport", "Network")):
            logger.error("Network error: %s", error_name)
            raise GeminiServiceError("Unable to connect to Vertex AI.") from exc
        logger.exception("Unexpected Gemini error")
        raise GeminiServiceError(
            "Something went wrong while generating the response."
        ) from exc

    text = (response.text or "").strip()
    if not text:
        raise GeminiServiceError("Gemini returned an empty response.")
    return text


if __name__ == "__main__":
    # Quick smoke test:  python -m services.gemini_service
    logging.basicConfig(level=logging.INFO)
    sample_resume = "Arya Sharma. Skills: Python, SQL, Docker. Project: Sales dashboard in Streamlit."
    print(generate_resume_response(sample_resume, "What are my technical skills?"))




def _build_config() -> types.GenerateContentConfig:
    config_args = {"max_output_tokens": settings.MAX_OUTPUT_TOKENS}

    # thinking_level sirf Gemini 3 models ke liye hai.
    # Gemini 2.5 mein hum thinking ka koi setting nahi bhejte (default use hoga).
    if settings.GEMINI_MODEL.startswith("gemini-3"):
        thinking_level = getattr(types.ThinkingLevel, settings.THINKING_LEVEL.upper())
        config_args["thinking_config"] = types.ThinkingConfig(thinking_level=thinking_level)

    return types.GenerateContentConfig(**config_args)