from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path
import uvicorn

app = FastAPI()
t_path = Path("src/templates").resolve()
templates = Jinja2Templates(directory=str(t_path))

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/chat")
async def chat(request: Request):
    data     = await request.json()
    message  = data.get("message", "")
    pdf_text = data.get("pdf_text", "")

    # Placeholder — swap this out for Ollama later
    reply = f"[stub] received: {message}"
    if pdf_text:
        reply += f" (+ PDF with {len(pdf_text)} chars)"

    return JSONResponse({"reply": reply})

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, log_level="info")