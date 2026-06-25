import os
import uvicorn
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from week_2.prompt_model import prompt_model
from week_2.find_skill_gaps import find_skill_gaps_from_text

WEEK2_DIR = Path(__file__).parent / "week_2"
DEFAULT_JOBS_DB = WEEK2_DIR / "data" / "jobs.db"
JOBS_DB_PATH = Path(os.environ.get("JOBS_DB_PATH", str(DEFAULT_JOBS_DB)))

app = FastAPI()

class ChatRequest(BaseModel):
    message: str
    pdf_text: str | None = None
    model: str = "llama3.2:latest"

class ChatResponse(BaseModel):
    reply: str

def format_skill_gap_result(result) -> str:
    gaps = ", ".join(result.gaps) if result.gaps else "none"
    skills = ", ".join(result.skill) if result.skill else "none"
    return f"Missing skills: {gaps}\nMatching skills: {skills}"

@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    if body.pdf_text:
        if not JOBS_DB_PATH.is_file():
            raise HTTPException(status_code=500, detail="Jobs database not found")

        result = find_skill_gaps_from_text(body.pdf_text, str(JOBS_DB_PATH))
        return ChatResponse(reply=format_skill_gap_result(result))

    reply = prompt_model(body.model, body.message)
    if reply is None:
        raise HTTPException(status_code=503, detail="Model unavailable")
    return ChatResponse(reply=reply)

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, log_level="info")
