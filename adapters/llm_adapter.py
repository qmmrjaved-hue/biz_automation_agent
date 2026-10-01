"""
llm_adapter.py — thin wrapper around Google Gemini (google-genai), shared by
every skill that needs classification, extraction, drafting, or SQL
generation, and by the controller for tool-calling based routing.

Retry-on-429 logic is ported from Voice2Query's text_to_sql.py, which proved
out this exact pattern against the Gemini API.

Public functions:
  - generate_text(prompt, system_instruction=None) -> str
  - generate_json(prompt, system_instruction=None) -> dict
  - generate_with_tools(contents, tools, system_instruction=None) -> str
"""

import json
import re
import time

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from config import settings

_MAX_RETRIES = 3


def _client() -> genai.Client:
    return genai.Client(api_key=settings.require_gemini_key())


def _strip_fences(text: str) -> str:
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text.strip())
    text = re.sub(r"\n?```$", "", text.strip())
    return text.strip()


def _call_with_retry(fn):
    """Run a Gemini call, retrying on 429 rate limits up to _MAX_RETRIES times."""
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return fn()
        except genai_errors.ClientError as e:
            if e.code == 429 and attempt < _MAX_RETRIES:
                wait = 35
                match = re.search(r"retry in ([\d.]+)s", str(e))
                if match:
                    wait = int(float(match.group(1))) + 5
                print(f"[llm_adapter] Rate limited (429). Waiting {wait}s "
                      f"before attempt {attempt + 1}/{_MAX_RETRIES} ...")
                time.sleep(wait)
            else:
                raise RuntimeError(f"[llm_adapter] Gemini API call failed: {e}") from e
        except Exception as e:
            raise RuntimeError(f"[llm_adapter] Gemini API call failed: {e}") from e
    raise RuntimeError("[llm_adapter] Gemini API call failed after retries.")


def generate_text(prompt: str, system_instruction: str = None) -> str:
    """
    Send a prompt to Gemini and return the plain-text response.

    Args:
        prompt:             The user-facing prompt / question.
        system_instruction: Optional system prompt steering the response.

    Returns:
        The stripped text response.

    Raises:
        EnvironmentError: if GEMINI_API_KEY is not set.
        RuntimeError: if the API call fails or returns an empty response.
    """
    client = _client()
    config = types.GenerateContentConfig(system_instruction=system_instruction) if system_instruction else None

    def _do():
        return client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=config,
        )

    response = _call_with_retry(_do)
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("[llm_adapter] Gemini returned an empty response.")
    return text


def generate_json(prompt: str, system_instruction: str = None) -> dict:
    """
    Send a prompt to Gemini and parse the response as JSON.

    Args:
        prompt:             The user-facing prompt / question.
        system_instruction: Optional system prompt; should instruct the model
                            to reply with JSON matching the expected shape.

    Returns:
        The parsed JSON object (dict or list).

    Raises:
        EnvironmentError: if GEMINI_API_KEY is not set.
        RuntimeError: if the API call fails or the response isn't valid JSON.
    """
    client = _client()
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
    )

    def _do():
        return client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=config,
        )

    response = _call_with_retry(_do)
    raw = _strip_fences((response.text or "").strip())
    if not raw:
        raise RuntimeError("[llm_adapter] Gemini returned an empty response.")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"[llm_adapter] Gemini did not return valid JSON: {raw!r}") from e


def generate_with_tools(contents, tools: list, system_instruction: str = None):
    """
    Run a Gemini call with automatic function calling over a list of plain
    Python callables. Gemini decides which tool(s) to call based on their
    name, type hints, and docstring; google-genai executes them locally and
    feeds the result back until a final text answer is produced.

    Args:
        contents:            The conversation so far (string, or list of
                             genai content parts for multi-turn context).
        tools:               List of Python callables to expose as tools.
        system_instruction:  Optional system prompt describing the agent's role.

    Returns:
        The final text response from Gemini after any tool calls resolve.

    Raises:
        EnvironmentError: if GEMINI_API_KEY is not set.
        RuntimeError: if the API call fails.
    """
    client = _client()
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=tools,
    )

    def _do():
        return client.models.generate_content(
            model=settings.gemini_model,
            contents=contents,
            config=config,
        )

    response = _call_with_retry(_do)
    return (response.text or "").strip()
