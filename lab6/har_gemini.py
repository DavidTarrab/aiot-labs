"""Task 2.1: Gemini requests; keys stay on the desktop, never on ESP32."""
import os
import time
from pathlib import Path
from har_common import build_prompt, parse_label

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")


def get_api_key():
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if key:
        return key
    # Reuse the existing Lab 5 configuration without copying its secret.
    for path in (Path(__file__).with_name(".gemini_api_key"),
                 Path(__file__).resolve().parent.parent / "lab5/.gemini_api_key"):
        if path.is_file():
            return path.read_text().strip()
    raise ValueError("Set GEMINI_API_KEY or configure .gemini_api_key")


def get_llm_response(prompt):
    from google import genai
    from google.genai import types, errors
    with genai.Client(api_key=get_api_key(),
                      http_options=types.HttpOptions(timeout=60000)) as client:
        for attempt in range(3):
            try:
                reply = client.models.generate_content(
                    model=MODEL, contents=prompt,
                    config=types.GenerateContentConfig(temperature=0, max_output_tokens=2048))
                break
            except errors.APIError as error:
                if error.code != 429 or attempt == 2:
                    raise
                print("Gemini quota reached; retrying in 55 seconds", flush=True)
                time.sleep(55)
    if not reply.text:
        raise RuntimeError("Gemini returned no text")
    return reply.text


def classify(data, style="direct", **metadata):
    prompt = build_prompt(data, style, **metadata)
    output = get_llm_response(prompt)
    result = {"label": None, "output": output, "prompt": prompt,
              "style": style, "model": MODEL}
    try:
        result["label"] = parse_label(output)
    except ValueError as error:
        # Retain the actual response for the report even when it cannot be parsed.
        result["parse_error"] = str(error)
    return result


if __name__ == "__main__":
    print(get_llm_response(input("Enter a prompt: ")))
