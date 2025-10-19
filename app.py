from fastapi import FastAPI

app = FastAPI()

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
        "pair": "SOL-USDC"
    }
