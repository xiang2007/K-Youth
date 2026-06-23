import os
import time
import sys
from dataclasses import dataclass
from dotenv import load_dotenv
from google import genai
from google.genai import types
from ollama import Client

load_dotenv()
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
ollama_client = Client(host=OLLAMA_HOST)
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

def prompt_model_extra(model: str, prompt: str) -> ModelResult | None:
    if "gemini" in model and noApi == 0:
        response = prompt_google(model, prompt)
        if not response: 
            print("Fallback to local llm")
            response = prompt_local_llm("llama3.1:latest", prompt)
            if not response:
                return None
    else:
        response = prompt_local_llm(model, prompt)
        if not response:
            return None
    return response


def prompt_model(model: str, prompt: str) -> str | None:
    if "gemini" in model and noApi != 1:
        response = prompt_google(model, prompt)
        if not response:
            print("Fallback to local llm")
            response = prompt_local_llm("llama3.1:latest", prompt)
            if not response:
                return None
    else:
        response = prompt_local_llm(model, prompt)
        if not response:
            return None
    return response.text

def prompt_google(model: str, prompt: str) -> ModelResult | None:
    total_token : int

    start = time.perf_counter()
    config = types.GenerateContentConfig(
            temperature=0.0
    )
    try:
        response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config
        )
    except Exception as e:
        print(f"Gemini error: {((e.args[0]).split(',', 5))[1]}")
        return None
    total_token = response.usage_metadata.total_token_count
    text = str(response.text)
    end = time.perf_counter()
    total_time = end - start
    return ModelResult(
        text=text,
        total_tokens=total_token,
        time_taken=total_time
    )

def prompt_local_llm(model: str, prompt: str) -> ModelResult | None:
    start = time.perf_counter()
    try:
        response = ollama_client.generate(
            model=model,
            prompt=prompt
        )
        text = response["response"]
        total_token = response["prompt_eval_count"] + response["eval_count"]
        end = time.perf_counter()
        total_time = end - start
    except Exception as e:
        print(f"Ollama error: {e}")
        return None
    return ModelResult(
        text=text,
        total_tokens=total_token,
        time_taken=total_time
    )

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python your_script.py <model> <prompt>")
        sys.exit(1)

    model = sys.argv[1]
    prompt = sys.argv[2]
    print(prompt_model(model, prompt))