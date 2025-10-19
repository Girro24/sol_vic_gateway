# app.py
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import os

app = FastAPI(title="SOL VIC Gateway")

# ---- health / status ----
@app.get("/")
def root():
    return {"message": "SOL VIC Gateway is live"}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/status")
def status():
    return {
        "status": "running",
        "exchange": "coinbase",
        "pair": os.getenv("SYMBOL", "SOL-USDC")
    }

# ---- webhook from TradingView (простая заглушка) ----
EXPECTED_KEY = os.getenv("EXPECTED_KEY", "")

class Alert(BaseModel):
    key: str
    action: str  # "buy" | "sell"
    symbol: str | None = None
    usd: float | None = None
    reason: str | None = None

@app.post("/hook")
async def hook(alert: Alert, request: Request):
    if not EXPECTED_KEY or alert.key != EXPECTED_KEY:
        raise HTTPException(status_code=401, detail="bad key")
    # Тут позже добавим вызов Coinbase API; пока просто эхо:
    return {"ok": True, "received": alert.model_dump()}
