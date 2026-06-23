from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path
import uvicorn
import httpx
import os

app = FastAPI()
t_path = Path("src/templates").resolve()
templates = Jinja2Templates(directory=str(t_path))
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BACKEND_URL}/chat",
            json=data,
            timeout=60.0,
        )

    if resp.status_code >= 400:
        # Forward the backend's error detail so the client (and logs) can see it
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        return JSONResponse({"error": detail}, status_code=resp.status_code)

    return JSONResponse(resp.json())


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, log_level="info")