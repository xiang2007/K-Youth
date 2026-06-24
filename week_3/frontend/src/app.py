from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path
import uvicorn
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
t_path = Path("src/templates").resolve()
templates = Jinja2Templates(directory=str(t_path))
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(
                f"{BACKEND_URL}/chat",
                json=data,
            )
        except httpx.ReadTimeout:
            return JSONResponse(
                {"error": "The request took too long. The AI model may be loading — try again in a moment."},
                status_code=504,
            )

    if resp.status_code >= 400:
        # Forward the backend's error detail so the client (and logs) can see it
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        return JSONResponse({"error": detail}, status_code=resp.status_code)

    try:
        return JSONResponse(resp.json())
    except httpx.InvalidJSONError:
        return JSONResponse(
            {"error": "Unexpected server response — please try again"},
            status_code=502,
        )


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8080, log_level="info")