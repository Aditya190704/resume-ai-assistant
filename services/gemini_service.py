"""All Gemini / Vertex AI communication lives in this file."""

import logging    # creates logs for debugging/errors
from functools import lru_cache   # reuses the gemini client instead of creating it repeatedly

from google import genai   # provides the gemini API Client
from google.auth.exceptions import GoogleAuthError   # raised when authentication fails
from google.genai import errors, types    # provides the gemini API error types and content generation types

from config import settings # imports the configuration settings from the config module
from prompts.resume_prompt import build_resume_prompt  # Creates the prompt containing resume + user question

logger = logging.getLogger(__name__)   # creates a logger object for logging messages in this module


class GeminiServiceError(Exception):            # it inherits from python's built in Exception
    """Raised with a user-friendly message when Gemini cannot answer."""     


@lru_cache(maxsize=1)          # maxsize means the cache stores one result, Dont create a gemini connection again and again/reuse it
def _get_client() -> genai.Client:
    """Create the Vertex AI client once. Uses Application Default Credentials."""
    return genai.Client(
        vertexai=True,
        project=settings.GCP_PROJECT_ID,
        location=settings.GCP_LOCATION,
    )      # creating connection client


def _build_config() -> types.GenerateContentConfig:
    config_args = {"max_output_tokens": settings.MAX_OUTPUT_TOKENS} # sets the maximum length of the gemini answer, to prevent unnecessarily huge responses

    # thinking_level sirf Gemini 3 models ke liye hai.
    # Gemini 2.5 mein hum thinking ka koi setting nahi bhejte (default use hoga).
    if settings.GEMINI_MODEL.startswith("gemini-3"):
        thinking_level = getattr(types.ThinkingLevel, settings.THINKING_LEVEL.upper())
        config_args["thinking_config"] = types.ThinkingConfig(thinking_level=thinking_level)

    return types.GenerateContentConfig(**config_args)


def _limit_resume_length(resume_text: str) -> str:    # it takes the extracted resume text and returns a safe size version of it
    if len(resume_text) > settings.MAX_RESUME_CHARS:   # counts the number of characters in the resume text
        logger.warning("Resume text truncated to %d characters", settings.MAX_RESUME_CHARS)   # if the resume is too long, the application records a warning in the logs
        return resume_text[: settings.MAX_RESUME_CHARS]  # this keeps only the first allowed number of characters
    return resume_text  # if the resume is within the limit, nothing is changed


def _api_error_message(exc: errors.APIError) -> str:  # it takes an API error and returns a normal text message
    code = getattr(exc, "code", None)   # it safely checks whether the error object has a code attribute
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


def generate_resume_response(resume_text: str, user_question: str) -> str:   # it takes two inputs resume_text, user_question and returns gemini's answer
    """Send resume + question to Gemini and return the answer text."""
    if not settings.GCP_PROJECT_ID:    # this checks whether the project id is available
        raise GeminiServiceError(
            "GCP_PROJECT_ID is not set. Please add it to your .env file."
        )

    prompt = build_resume_prompt(_limit_resume_length(resume_text), user_question)  # make sure the resume isnt excessively large, then combines system instructions, resume content, user question, into one final prompt

    try:         # this is the actual Gemini API call, _get_client() creates a connection to the Gemini API, and generate_content() sends the prompt to Gemini and gets the response
        response = _get_client().models.generate_content(   # generate the answer using the provided content
            model=settings.GEMINI_MODEL,
            contents=prompt,   # this is actual prommpt sent to gemini
            config=_build_config(),     # provides generation settiings such as max_output_tokens and thinking level
        )
    except GoogleAuthError as exc:  # this catches the google authentication problems
        logger.error("Google auth error: %s", type(exc).__name__)   # records the technical error logs
        raise GeminiServiceError(
            "Authentication failed. Please check your Google Cloud credentials."
        ) from exc   # shows a simple error to the application/user.
    except errors.APIError as exc:    # this catches error returned by the Gemini/Vertex AI API
        logger.error("Vertex AI API error: code=%s", getattr(exc, "code", None)) # record the API error code
        raise GeminiServiceError(_api_error_message(exc)) from exc  # call the function we discussed earlier which converts Model or location not found. Please check GEMINI_MODEL and GCP_LOCATION

    except Exception as exc:   # if some unexpected error occurs that wasnt handled above , it comes here
        error_name = type(exc).__name__    # example: error_name = "TimeoutError" or "ConnectionError" or "NetworkError" etc
        if any(word in error_name for word in ("Connect", "Timeout", "Transport", "Network")): # this checks whether the error name contains related to network problems
            logger.error("Network error: %s", error_name)
            raise GeminiServiceError("Unable to connect to Vertex AI.") from exc
        logger.exception("Unexpected Gemini error") # logs the complete unexpected error information
        raise GeminiServiceError(
            "Something went wrong while generating the response."
        ) from exc  # shows the generic user-friendly error message to the application/user

    text = (response.text or "").strip() # this gets the actual text generated by Gemini, strip() removes unneccessary spaces
    if not text:
        raise GeminiServiceError("Gemini returned an empty response.") # if gemini returned nothing 
    return text 


if __name__ == "__main__":
    # Quick smoke test:  python -m services.gemini_service
    logging.basicConfig(level=logging.INFO)
    sample_resume = "Arya Sharma. Skills: Python, SQL, Docker. Project: Sales dashboard in Streamlit."
    print(generate_resume_response(sample_resume, "What are my technical skills?"))




def _build_config() -> types.GenerateContentConfig: # while generating gemini answer which settings have to use - prepare that
    config_args = {"max_output_tokens": settings.MAX_OUTPUT_TOKENS} # Agar settings.MAX_OUTPUT_TOKENS = 8192 hai, toh Gemini ko maximum output limit 8192 tokens di jayegi.

    # thinking_level sirf Gemini 3 models ke liye hai.
    # Gemini 2.5 mein hum thinking ka koi setting nahi bhejte (default use hoga).
    if settings.GEMINI_MODEL.startswith("gemini-3"):
        thinking_level = getattr(types.ThinkingLevel, settings.THINKING_LEVEL.upper())
        config_args["thinking_config"] = types.ThinkingConfig(thinking_level=thinking_level)

    return types.GenerateContentConfig(**config_args)