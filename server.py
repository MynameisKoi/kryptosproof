"""
HTTP entrypoint for Cloud Run — must bind to 0.0.0.0:$PORT.
Batch audits remain: `python main.py [target_url]`.
"""
from fastapi import FastAPI

app = FastAPI(title="KryptoSproof", version="0.1.0")


@app.get("/")
@app.get("/health")
def health():
    return {"status": "ok", "service": "kryptosproof"}
