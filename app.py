import os, hmac, hashlib, time, json, base64
import httpx
from fastapi import FastAPI, Request, HTTPException

app = FastAPI(title="SOL VIC Gateway")

# ================= ENV =================
# Shared secret with TradingView (or a static key placed in payload)
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")          # recommend: long random string
# If you prefer a simple key inside JSON instead of header signature,
# set EXPECTED_KEY and use it; see check below.
EXPECTED_KEY = os.getenv("EXPECTED_KEY", "")              # optional alternative to HMAC header

EXCHANGE = os.getenv("EXCHANGE", "coinbase")              # 'coinbase' (extensible to others)
SYMBOL = os.getenv("SYMBOL", "SOL-USDC")                  # Coinbase product_id style
BASE_ORDER_USD = float(os.getenv("BASE_ORDER_USD", "25")) # default USD quote size per trade

GOOGLESHEET_WEBAPP = os.getenv("GOOGLESHEET_WEBAPP", "")  # optional: Google Apps Script Web App URL

# ===== Coinbase Advanced Trade API =====
CB_API_KEY = os.getenv("CB_API_KEY", "")
CB_API_SECRET = os.getenv("CB_API_SECRET", "")
# Advanced Trade usually doesn't require a passphrase (legacy Pro did).
CB_API_PASSPHRASE = os.getenv("CB_API_PASSPHRASE", "")    # keep for compatibility if enabled on your account
CB_API_BASE = os.getenv("CB_API_BASE", "https://api.coinbase.com/api/v3")

# ================== Security ==================
def verify_hmac(raw_body: bytes, signature_hex: str) -> bool:
    """
    Verifies HMAC-SHA256 of the raw request body using WEBHOOK_SECRET.
    TradingView cannot set custom headers natively; if you cannot pass X-Signature,
    use EXPECTED_KEY in payload instead (see below).
    """
    if not WEBHOOK_SECRET or not signature_hex:
        return False
    mac = hmac.new(WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, signature_hex)

# ================== Logging ====================
async def log_event(payload: dict, resp: dict | None = None):
    """
    Sends a log row to a Google Apps Script Web App (optional).
    """
    if not GOOGLESHEET_WEBAPP:
        return
    data = {
        "ts": int(time.time()),
        "symbol": payload.get("symbol"),
        "action": payload.get("action"),
        "reason": payload.get("reason"),
        "usd": payload.get("usd"),
        "response": json.dumps(resp, ensure_ascii=False) if resp else ""
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(GOOGLESHEET_WEBAPP, json=data)
    except Exception:
        # best-effort logging
        pass

# ============== Coinbase Adapter ===============
async def coinbase_market_order(side: str, usd_amount: float, product_id: str):
    """
    Places a simple MARKET IOC order on Coinbase Advanced Trade using quote_size (USDC).
    Check Coinbase docs for any changes before production.
    """
    endpoint_path = "/api/v3/brokerage/orders"
    endpoint = f"{CB_API_BASE}/brokerage/orders".replace("/api/v3", "").rstrip("/") + endpoint_path  # keep path stable

    body = {
        "client_order_id": f"vic_{int(time.time()*1000)}",
        "product_id": product_id,          # e.g., 'SOL-USDC'
        "side": side.lower(),              # 'buy' | 'sell'
        "order_configuration": {
            "market_market_ioc": {
                "quote_size": f"{usd_amount:.2f}"
            }
        }
    }
    ts = str(int(time.time()))
    # Prehash format: timestamp + method + request_path + body_json (no base URL)
    prehash = ts + "POST" + endpoint_path + json.dumps(body, separators=(",", ":"))
    signature = hmac.new(CB_API_SECRET.encode(), prehash.encode(), hashlib.sha256).digest()
    sign_b64 = base64.b64encode(signature).decode()

    headers = {
        "Content-Type": "application/json",
        "CB-ACCESS-KEY": CB_API_KEY,
        "CB-ACCESS-SIGN": sign_b64,
        "CB-ACCESS-TIMESTAMP": ts,
    }
    # Some accounts may require a passphrase header (legacy). Safe to include if set.
    if CB_API_PASSPHRASE:
        headers["CB-ACCESS-PASSPHRASE"] = CB_API_PASSPHRASE

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(endpoint, json=body, headers=headers)
        # raise for HTTP errors to propagate to client
        r.raise_for_status()
        return r.json()

async def place_order(action: str, usd_amount: float, symbol: str):
    side = "BUY" if action.lower() in ("buy", "start_long", "open_long") else "SELL"
    if EXCHANGE == "coinbase":
        return await coinbase_market_order(side, usd_amount, symbol)
    raise HTTPException(status_code=400, detail=f"Unsupported exchange: {EXCHANGE}")

# ================== Routes =====================
@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/hook")
async def hook(req: Request):
    raw = await req.body()

    # Option A: header signature (if your sender can set it)
    signature = req.headers.get("X-Signature", "")
    if WEBHOOK_SECRET:
        if not verify_hmac(raw, signature):
            # If HMAC path fails, fall back to EXPECTED_KEY check below
            pass

    try:
        payload = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Bad JSON")

    # Option B: simple key inside payload (works with TradingView)
    if EXPECTED_KEY and payload.get("key") != EXPECTED_KEY:
        raise HTTPException(status_code=401, detail="Bad key")

    # Expected payload: {"action":"buy|sell", "symbol":"SOL-USDC", "reason":"VIC_bull", "usd": 25}
    action = payload.get("action", "buy")
    symbol = payload.get("symbol", SYMBOL)
    usd = float(payload.get("usd", BASE_ORDER_USD))

    resp = await place_order(action, usd, symbol)
    await log_event(payload, resp)

    return {"ok": True, "placed": {"action": action, "usd": usd, "symbol": symbol}, "resp": resp}
