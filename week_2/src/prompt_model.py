import os
import time
import ollama
from dataclasses import dataclass
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.types import GenerateContentResponse
from ollama import generate, _types

load_dotenv()

noApi = 0

try:
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
except ValueError:
    print("No API key was provided")
    noApi = 1

@dataclass
class ModelResult:
    text: str
    total_tokens: int
    time_taken: float

def prompt_model(model: str, prompt: str) -> ModelResult | None:
    start = time.perf_counter()

    if "gemini" in model and noApi != 1:
        try:
            response = prompt_google(model, prompt)
            total_tokens = response.usage_metadata.total_token_count
            text = str(response.text)
        except Exception as e:
            print(f"Google Genai Error {str(e.args[0]).split('{')}")
            print("Fallback to local llm")
            response = prompt_local_llm("lama3.1:latest", prompt)
            if not response:
                return None
            text = response["response"]
            total_tokens = response['prompt_eval_count'] + response['eval_count']

    else:
        response = prompt_local_llm(model, prompt)
        if not response:
            return None
        text = response["response"]
        total_tokens = response['prompt_eval_count'] + response['eval_count']

    end = time.perf_counter()
    elapsed = end - start

    return ModelResult(
        text=text,
        total_tokens=total_tokens,
        time_taken=elapsed
    )

def prompt_google(model: str, prompt: str) -> GenerateContentResponse:
    config = types.GenerateContentConfig(
            temperature=0.0
        )
    response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config
        )
    return response

def prompt_local_llm(model: str, prompt: str) -> GenerateResponse:
    try:
        response = generate(
                model=model,
                prompt=prompt
            )
    except Exception as e:
        print(f"Ollama error: {e}")
        return None
    return response