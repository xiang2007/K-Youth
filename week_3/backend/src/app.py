import os
import sys
import tempfile
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

WEEK2_DIR = Path(__file__).parent / "week_2"
sys.path.insert(0, str(WEEK2_DIR))

from find_skill_gaps import find_skill_gaps  # noqa: E402
from prompt_model import prompt_model  # noqa: E402

DEFAULT_JOBS_DB = WEEK2_DIR / "data" / "jobs_d3_eval.db"
JOBS_DB_PATH = Path(os.environ.get("JOBS_DB_PATH", DEFAULT_JOBS_DB))

app = FastAPI()


class ChatRequest(BaseModel):
    message: str
    pdf_text: str | None = None
    model: str = "llama3.1:latest"


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

        temp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(body.pdf_text)
                temp_path = tmp.name

            result = find_skill_gaps(temp_path, str(JOBS_DB_PATH))
            return ChatResponse(reply=format_skill_gap_result(result))
        finally:
            if temp_path:
                Path(temp_path).unlink(missing_ok=True)

    reply = prompt_model(body.model, body.message)
    if reply is None:
        raise HTTPException(status_code=503, detail="Model unavailable")
    return ChatResponse(reply=reply)


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, log_level="info")
