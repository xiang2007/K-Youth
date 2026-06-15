import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from ollama import generate

def prompt_model(model: str, prompt: str) -> str:

    if "gemini" in model:
        load_dotenv()
        key = os.getenv("GOOGLE_API_KEY")
        client = genai.Client(api_key=key)
        
        # Gemini uses the types configuration
        config = types.GenerateContentConfig(
            temperature=0.0  # Stable and fast for Gemini
        )
        
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config
        )
        print(f"Token used: {response.usage_metadata.total_token_count}")
        return response.text
        
    else:
        if "qwen" in model:
            response = generate(
            model=model,
            prompt=prompt,
            options={
            'temperature': 0.0,
            'num_predict': 50,
            'keep_alive': 0
        }
        )
        else:
            response = generate(
                model=model, 
                prompt=prompt,
                options={
                    'temperature': 0.3
                }
            )
        res = response['response']
        print(f"Total tokens: {response['prompt_eval_count'] + response['eval_count']}")
    return res