# Bitcoin Trading Bot

## Project Summary

A minimal web-based trading interface for CME Micro Bitcoin Futures (MBT) via Interactive Brokers, built for a Canadian trader who needs long/short BTC exposure with leverage.

**Why IBKR + CME Futures:** Canada bans crypto leverage/shorting on registered platforms. IBKR is the regulated workaround -- CME Micro BTC Futures provide 5-7x leverage, long/short capability, and ~23hr/day trading. See `RESEARCH.md` for full analysis of alternatives considered.

## Architecture

```
frontend/          React + Vite (TypeScript)
  ├── Candlestick chart (TradingView lightweight-charts)
  ├── Long / Short buttons
  ├── Position & P/L display
  └── Simple auth (login page)

backend/           Python + FastAPI
  ├── WebSocket endpoint → streams candle data to frontend
  ├── REST endpoints → place orders, get positions, auth
  ├── ib_insync → connects to IB Gateway
  └── Market data polling → 1-min candles from IBKR

IB Gateway         Runs locally, paper trading first
  └── Connects to CME for MBT (Micro Bitcoin Futures)
```

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | React + Vite + TypeScript | Fast dev, modern tooling |
| Charts | TradingView lightweight-charts v5 | Free, fast, purpose-built for financial charts |
| Styling | Tailwind CSS | Minimal config, utility-first |
| Backend | Python + FastAPI | Async, WebSocket support, fast |
| IBKR Connection | ib_insync | Best Python IBKR library, async-compatible |
| Auth | Simple JWT (personal use) | Not production-grade, just keeps the UI gated |

## IBKR Setup Requirements

- IBKR account with **futures trading permissions**
- **CME market data subscription** (~$10-15/month non-professional)
- **IB Gateway** running locally (or TWS in API mode)
  - Gateway port: 4002 (paper), 4001 (live)
  - API connections enabled in Gateway settings
- Start with **paper trading** (port 4002) during development

## Contract Details

| Field | Value |
|---|---|
| Symbol | MBT |
| Exchange | CME |
| Contract size | 0.1 BTC |
| Currency | USD |
| Margin | ~$1,500-2,000 per contract |
| Effective leverage | ~5-7x |
| Trading hours | Sun 5PM - Fri 4PM CT (23hrs/day, 1hr break) |

## Setup

```bash
# 1. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env: set JWT_SECRET, USERNAME, PASSWORD_HASH

# 2. Generate a password hash
python -c "from passlib.hash import bcrypt; print(bcrypt.hash('yourpassword'))"

# 3. Start IB Gateway on localhost:4002 (paper) or :4001 (live)
```

## Key Commands

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm install
npm run dev

# IB Gateway must be running on localhost:4002 (paper) or :4001 (live)
```

## API Endpoints

```
POST   /api/auth/login          → JWT token
GET    /api/positions            → current positions & P/L
POST   /api/order                → { side: "BUY"|"SELL", quantity: 1 }
GET    /api/account              → account summary (balance, margin)
WS     /api/ws/candles           → streams 1-min candle updates
GET    /api/candles/history      → historical 1-min candles
```

## Key Files

- `RESEARCH.md` -- Regulatory research, cost analysis, why we chose IBKR + CME futures
- `backend/main.py` -- FastAPI app entry point
- `backend/ibkr.py` -- IBKR connection and trading logic via ib_insync
- `backend/models.py` -- Pydantic models
- `frontend/src/App.tsx` -- Main app component
- `frontend/src/components/Chart.tsx` -- Candlestick chart
- `frontend/src/components/TradePanel.tsx` -- Long/Short buttons + quantity selector
- `frontend/src/components/PositionBar.tsx` -- Position display with unrealized P/L
- `frontend/src/api.ts` -- Fetch wrapper with JWT auth, WebSocket helper
- `frontend/src/types.ts` -- TypeScript types matching backend models
- `backend/.env.example` -- Environment config template

## Development Notes

- Always develop against **paper trading** (port 4002) first
- Never commit secrets or auth tokens
- The backend must be running before the frontend can show live data
- IB Gateway disconnects after inactivity -- the backend should handle reconnection
