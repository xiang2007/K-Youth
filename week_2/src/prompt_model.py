from google import genai
from google.genai import types
from ollama import generate
from dotenv import load_dotenv
import os

def prompt_model(model: str, prompt: str) -> str :

    if "gemini" in model:
        load_dotenv()
        key = os.getenv("GOOGLE_API_KEY")
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=model,
            contents=prompt
        )
        return (response.text)
    else:
        response = generate(model, prompt)
        res = response['response']
    return (res)