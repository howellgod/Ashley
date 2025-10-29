import os
import sys
import argparse
from pathlib import Path
from openai import AzureOpenAI
from urllib.parse import urlparse
from dotenv import load_dotenv

def _load_envs() -> None:
    """Load environment variables from common locations.

    Search order (first wins for each key unless already set in process env):
    1) Current working directory /.env
    2) Package directory (Ashley)/.env
    3) Project root (parent of Ashley)/.env
    """
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]
    for p in candidates:
        try:
            load_dotenv(dotenv_path=p, override=False)
        except Exception:
            # Ignore load errors; we'll surface missing values later in get_env
            pass


# Load variables from .env files early so main and imports can read them
_load_envs()


def get_env(name: str, required: bool = True, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value or ""


def build_client() -> AzureOpenAI:
    # Ensure .env is loaded (idempotent)
    _load_envs()
    endpoint_raw = get_env("AZURE_OPENAI_ENDPOINT")
    # Normalize endpoint to base resource URL if a full path was provided
    def _normalize_endpoint(url: str) -> str:
        try:
            parts = urlparse(url)
            if parts.scheme and parts.netloc:
                return f"{parts.scheme}://{parts.netloc}"
        except Exception:
            pass
        return url

    endpoint = _normalize_endpoint(endpoint_raw)
    api_key = get_env("AZURE_OPENAI_API_KEY")
    api_version = get_env("AZURE_OPENAI_API_VERSION", required=False, default="2024-12-01-preview")
    return AzureOpenAI(api_version=api_version, azure_endpoint=endpoint, api_key=api_key)


def chat_example(
    client: AzureOpenAI,
    deployment: str,
    user_content: str,
    system_content: str = "You are a helpful assistant.",
    max_tokens: int = 4096,
    temperature: float = 1.0,
) -> str:
    resp = client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=1.0,
        model=deployment,
    )
    return resp.choices[0].message.content


def chat_stream(
    client: AzureOpenAI,
    deployment: str,
    user_content: str,
    system_content: str = "You are a helpful assistant.",
    max_tokens: int = 4096,
    temperature: float = 1.0,
):
    """Yield content tokens as they arrive from Azure OpenAI."""
    stream = client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=1.0,
        model=deployment,
        stream=True,
    )
    try:
        for event in stream:
            # New SDK emits chunk objects with choices[0].delta.content
            try:
                delta = getattr(event.choices[0].delta, "content", None)
            except Exception:
                # Some events may not include content (e.g., role/tool signals); skip
                delta = None
            if delta:
                yield delta
    finally:
        try:
            stream.close()
        except Exception:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chat with Azure OpenAI.")
    parser.add_argument("prompt", nargs="*", help="User input prompt. If omitted, you'll be prompted interactively.")
    parser.add_argument("--deployment", dest="deployment", default=None, help="Override deployment name; defaults to AZURE_OPENAI_DEPLOYMENT.")
    parser.add_argument("--system", dest="system", default=os.getenv("AZURE_OPENAI_SYSTEM", "You are a helpful assistant."), help="System prompt.")
    parser.add_argument("--max-tokens", dest="max_tokens", type=int, default=512)
    parser.add_argument("--temperature", dest="temperature", type=float, default=0.7)
    parser.add_argument("--dry-run", action="store_true", help="Print the request that would be sent and exit.")
    args = parser.parse_args()

    # Compose user content from args or stdin
    user_content = " ".join(args.prompt).strip()
    if not user_content:
        try:
            user_content = input("Enter your message: ").strip()
        except EOFError:
            user_content = ""
    if not user_content:
        raise SystemExit("No user input provided.")

    # For dry-run, don't require env vars; show placeholder if missing
    if args.dry_run:
        deployment = args.deployment or os.getenv("AZURE_OPENAI_DEPLOYMENT", "<missing>")
        print("Dry run: would send messages ->")
        print({
            "model": deployment,
            "messages": [
                {"role": "system", "content": args.system},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": args.max_tokens,
            "temperature": args.temperature,
        })
        sys.exit(0)

    deployment = args.deployment or get_env("AZURE_OPENAI_DEPLOYMENT")

    client = build_client()
    print(chat_example(client, deployment, user_content, args.system, args.max_tokens, args.temperature))
