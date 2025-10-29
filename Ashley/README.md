# Azure OpenAI quick chat

This script calls an Azure OpenAI chat deployment using the official `openai` Python SDK.

## Prerequisites
- Python 3.9+
- Your Azure OpenAI resource with a chat deployment
- Environment variables set for endpoint, key, and deployment

## Setup

## Deploy to Azure Web Apps (Linux)

This project includes a small FastAPI server (`app.py`) exposing:
- `GET /health` for health checks
- `POST /chat` with body `{ "prompt": "...", "system?": "...", "max_tokens?": 512, "temperature?": 0.7, "deployment?": "..." }`

### 1) Prereqs
- Azure subscription and `az` CLI installed
- Python runtime on Azure App Service supports Python 3.10+
- Your Azure OpenAI resource with a chat deployment

### 2) Install deps locally
```powershell
1. Create and/or activate your environment (you are using `conda` env `i3`).
```

### 3) Create Azure resources
```powershell
2. Install dependencies:

```powershell
C:/Users/howel/anaconda3/envs/i3/python.exe -m pip install -r "c:\\Users\\howel\\OneDrive - Anansi Analytics\\AI\\t2\\requirements.txt"
```

3. Set required environment variables (PowerShell):

```powershell
$env:AZURE_OPENAI_ENDPOINT = "https://<your-resource>.openai.azure.com/"
$env:AZURE_OPENAI_API_KEY = "<your-key>"
$env:AZURE_OPENAI_DEPLOYMENT = "<your-deployment-name>"
# Optional (defaults to 2024-12-01-preview):

### 4) Configure app settings
```powershell
$env:AZURE_OPENAI_API_VERSION = "2024-12-01-preview"
```

## Run

```powershell
# Dry run (no network call) with a prompt
C:/Users/howel/anaconda3/envs/i3/python.exe "c:\\Users\\howel\\OneDrive - Anansi Analytics\\AI\\t2\\agent.py" --dry-run "I am going to Paris, what should I see?"

# Actual call (requires valid env vars)

### 5) Deploy code (zip deploy)
```powershell
C:/Users/howel/anaconda3/envs/i3/python.exe "c:\\Users\\howel\\OneDrive - Anansi Analytics\\AI\\t2\\agent.py" "I am going to Paris, what should I see?"
```

## Notes
- Secrets are no longer hardcoded in code. Use env vars (or your secret manager) instead.

### 6) Test
```powershell
- If you previously saw `ModuleNotFoundError: No module named 'azure.ai'`, installing requirements resolves it.
- You can also manage secrets via Azure Key Vault and inject them into your runtime for production.

### CLI options
- `--deployment` to override `AZURE_OPENAI_DEPLOYMENT`
- `--system` to override the system prompt

### Notes & best practices
- Don’t commit secrets. Use App Settings or Key Vault references.
- Ensure `WEBSITES_PORT=8000` and your app listens on that port.
- Use `gunicorn` on Linux; for Windows plans use `python -m uvicorn app:app --host 0.0.0.0 --port %PORT%` as startup.
- Scale up/out in App Service Plan as needed. Enable Application Insights for logs/metrics.
- `--max-tokens` and `--temperature` to adjust generation
- `--dry-run` to print the request payload without calling the service
