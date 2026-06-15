import os
import time
from dataclasses import dataclass
from dotenv import load_dotenv
from google import genai
from google.genai import types
from ollama import generate

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

@dataclass
class ModelResult:
    text: str
    total_tokens: int
    time_taken: float

def prompt_model(model: str, prompt: str) -> ModelResult:
    start = time.perf_counter()

    if "gemini" in model:
        config = types.GenerateContentConfig(
            temperature=0.0
        )
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config
        )
        total_tokens = response.usage_metadata.total_token_count
        text = str(response.text)

    else:
        response = generate(
            model=model,
            prompt=prompt
        )

        text = response["response"]
        total_tokens = response['prompt_eval_count'] + response['eval_count']

    end = time.perf_counter()
    elapsed = end - start

    return ModelResult(
        text=text,
        total_tokens=total_tokens,
        time_taken=elapsed
    )