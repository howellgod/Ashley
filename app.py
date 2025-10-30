import os
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel, Field

from Ashley.agent import build_client, chat_example, chat_stream, get_env

app = FastAPI(title="Agent Ashley")

# Lazy-initialized Azure OpenAI client and deployment
aoai_client = None  # type: ignore
default_deployment: Optional[str] = os.getenv("AZURE_OPENAI_DEPLOYMENT")


@app.on_event("startup")
def _init_clients() -> None:
    """Initialize the Azure OpenAI client at startup without crashing the app
    if environment variables are missing. Requests will surface a clear 503.
    """
    global aoai_client, default_deployment
    try:
        aoai_client = build_client()
        if not default_deployment:
            # Only require the deployment if not provided per-request
            default_deployment = get_env("AZURE_OPENAI_DEPLOYMENT", required=False)
    except Exception as e:
        # Don't crash on startup; log a hint. Handlers will check and return 503.
        print(f"[startup] Azure OpenAI client init failed: {e}")

# Static files and templates (live under the package directory 'Ashley')
BASE_DIR = Path(__file__).parent
PACKAGE_DIR = BASE_DIR / "Ashley"
app.mount("/static", StaticFiles(directory=str(PACKAGE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))


class ChatRequest(BaseModel):
    prompt: str = Field(..., description="User input prompt")
    system: Optional[str] = Field(default="You are a helpful assistant.")
    max_tokens: Optional[int] = Field(default=4096, ge=1, le=4096)
    temperature: Optional[float] = Field(default=1.0, ge=0.0, le=2.0)
    deployment: Optional[str] = Field(default=None, description="Override deployment name")


class ChatResponse(BaseModel):
    content: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    try:
        if aoai_client is None:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Service not configured. Set AZURE_OPENAI_ENDPOINT, "
                    "AZURE_OPENAI_API_KEY, and AZURE_OPENAI_DEPLOYMENT in App Settings."
                ),
            )

        deployment = req.deployment or default_deployment
        if not deployment:
            raise HTTPException(status_code=503, detail="Missing deployment name. Set AZURE_OPENAI_DEPLOYMENT or pass 'deployment'.")
        content = chat_example(
            client=aoai_client,
            deployment=deployment,
            user_content=req.prompt,
            system_content=req.system or "You are a helpful assistant.",
            max_tokens=req.max_tokens or 4096,
            temperature=req.temperature or 1.0,
        )
        return ChatResponse(content=content)
    except Exception as e:
        # In production you might want to log details and return a user-friendly message
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
def chat_streaming(req: ChatRequest):
    """Stream the model response tokens as plain text chunks."""
    try:
        if aoai_client is None:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Service not configured. Set AZURE_OPENAI_ENDPOINT, "
                    "AZURE_OPENAI_API_KEY, and AZURE_OPENAI_DEPLOYMENT in App Settings."
                ),
            )
        deployment = req.deployment or default_deployment
        if not deployment:
            raise HTTPException(status_code=503, detail="Missing deployment name. Set AZURE_OPENAI_DEPLOYMENT or pass 'deployment'.")

        def token_gen():
            for token in chat_stream(
                client=aoai_client,
                deployment=deployment,
                user_content=req.prompt,
                system_content=req.system or "You are a helpful assistant.",
                max_tokens=req.max_tokens or 4096,
                temperature=req.temperature or 1.0,
            ):
                yield token
            # Ensure a final flush boundary
            yield "\n"

        return StreamingResponse(
            token_gen(),
            media_type="text/plain; charset=utf-8",
            headers={
                "Cache-Control": "no-cache, no-transform",
                # Hint some proxies not to buffer (ignored if not applicable)
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})
