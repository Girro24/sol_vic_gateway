# SOL VIC Gateway (TradingView → Coinbase)

Minimal webhook gateway: TradingView alerts → FastAPI → Coinbase Advanced Trade (market order) → optional Google Sheets log.

## Files
- `app.py` — FastAPI server (webhook `/hook`, health `/health`)
- `requirements.txt` — deps
- `Procfile` — for Render
- `.env.example` — template for environment variables
- `tradingview/sol_vic_mvp.pine` — Pine v5 indicator with alerts
- `scripts/apps_script.gs` — Google Apps Script Web App to log events to a Sheet

## Deploy (Render.com quick)
1. Create new **Web Service** from this folder/repo.
2. **Runtime**: Python 3.11+.
3. **Start command**: `uvicorn app:app --host 0.0.0.0 --port 10000` (or use the provided Procfile).
4. Set **Environment Variables** from `.env.example` (copy values).
5. Deploy. Open `/health` — should return `{"ok": true}`.

## TradingView Alerts
- Webhook URL: `https://<your-app>.onrender.com/hook`
- Message JSON (BUY example):
```json
{
  "key": "change_me_super_long_secret",
  "action": "buy",
  "symbol": "SOL-USDC",
  "reason": "VIC_bull",
  "usd": 25
}
```
- SELL/EXIT alert: set `"action": "sell"`.

## Pine script (attach to SOL/USDC chart)
Use `tradingview/sol_vic_mvp.pine`, add to chart, then create two alerts:
- **BUY_SOL** with the BUY JSON above
- **EXIT_SOL** with the SELL JSON

## Google Sheets logging (optional)
1. Create a Google Sheet.
2. Open **Extensions → Apps Script**, paste `scripts/apps_script.gs`, set your sheet name.
3. Deploy **New deployment → Web app**; access: "Anyone with link".
4. Put the web app URL into `GOOGLESHEET_WEBAPP` env var.
5. Each order event will append a row.

## Notes / Safety
- This is a minimal gateway for MVP. Before live trading, add: retries on 5xx, idempotency by client_order_id, better auth.
- Coinbase Advanced Trade API paths/headers can change. Always verify with official docs.
- Run small sizes first and test in paper/sandbox if available.
