import os, hmac, hashlib, time, json, base64
import httpx
from fastapi import FastAPI, Request, HTTPException

app = FastAPI(title="SOL VIC Gateway")

# ================= ENV =================
EXPECTED_KEY   = os.getenv("EXPECTED_KEY", "SOL-GW-2025-KEY")
EXCHANGE       = os.getenv("EXCHANGE", "coinbase")
SYMBOL         = os.getenv("SYMBOL", "SOL-USDC")
BASE_ORDER_USD = float(os.getenv("BASE_ORDER_USD", "10"))

CB_API_KEY     = os.getenv("CB_API_KEY", "")
CB_API_SECRET  = os.getenv("CB_API_SECRET", "")
CB_API_BASE    = os.getenv("CB_API_BASE", "https://api.coinbase.com")

# ================= HEALTH =================
@app.get("/")
def root():
    return {"message": "SOL VIC Gateway is live"}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/status")
def status():
    return {"status": "running", "exchange": EXCHANGE, "pair": SYMBOL}

# ================= COINBASE ORDER =================
async def coinbase_market_order(side: str, usd_amount: float, product_id: str):
    endpoint_path = "/api/v3/brokerage/orders"
    url = f"{CB_API_BASE}{endpoint_path}"

    body = {
        "client_order_id": f"vic_{int(time.time()*1000)}",
        "product_id": product_id,
        "side": side.lower(),
        "order_configuration": {
            "market_market_ioc": {"quote_size": f"{usd_amount:.2f}"}
        }
    }

    ts = str(int(time.time()))
    prehash = ts + "POST" + endpoint_path + json.dumps(body, separators=(",", ":"))
    signature = hmac.new(CB_API_SECRET.encode(), prehash.encode(), hashlib.sha256).digest()
    sign_b64 = base64.b64encode(signature).decode()

    headers = {
        "Content-Type": "application/json",
        "CB-ACCESS-KEY": CB_API_KEY,
        "CB-ACCESS-SIGN": sign_b64,
        "CB-ACCESS-TIMESTAMP": ts,
    }

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, json=body, headers=headers)
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.json()

# ================= HOOK =================
@app.post("/hook")
async def hook(req: Request):
    payload = await req.json()
    if payload.get("key") != EXPECTED_KEY:
        raise HTTPException(status_code=401, detail="Bad key")

    action = payload.get("action", "buy")
    usd    = float(payload.get("usd", BASE_ORDER_USD))
    symbol = payload.get("symbol", SYMBOL)
    reason = payload.get("reason", "manual")

    print(f"[HOOK] {action} {symbol} ${usd} ({reason})")

    if EXCHANGE != "coinbase":
        raise HTTPException(status_code=400, detail=f"Unsupported exchange: {EXCHANGE}")

    resp = await coinbase_market_order(action, usd, symbol)
    return {"ok": True, "exchange": EXCHANGE, "placed": resp}
