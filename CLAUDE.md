# Bitcoin Trading Bot

## Project Summary

A minimal web-based trading interface for CME Micro Bitcoin Futures (MBT) via Interactive Brokers, built for a Canadian trader who needs long/short BTC exposure with leverage.

**Why IBKR + CME Futures:** Canada bans crypto leverage/shorting on registered platforms. IBKR is the regulated workaround -- CME Micro BTC Futures provide 5-7x leverage, long/short capability, and ~23hr/day trading. See `RESEARCH.md` for full analysis of alternatives considered.

## Architecture

```
Railway (cloud)
  └── Docker container
        ├── Tailscale (userspace) → connects to home server via tailnet
        ├── FastAPI backend → REST + WebSocket API
        └── Static files → built React frontend

Home server
  ├── Tailscale → mesh VPN to Railway
  └── IB Gateway (Docker) → connects to CME for MBT futures
```

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | React + Vite + TypeScript | Fast dev, modern tooling |
| Charts | TradingView lightweight-charts v5 | Free, fast, purpose-built for financial charts |
| Styling | Tailwind CSS | Minimal config, utility-first |
| Backend | Python + FastAPI | Async, WebSocket support, fast |
| IBKR Connection | ib_insync | Best Python IBKR library, async-compatible |
| Auth | Simple JWT + plaintext password | Personal use, just keeps the UI gated |
| Networking | Tailscale | Secure mesh VPN between Railway and home server |
| Deployment | Railway + Docker | Single container, auto-deploy from GitHub |

## Deployment

The app runs as a single Docker container on Railway. IB Gateway runs on a home server. They communicate over Tailscale.

### Railway env vars

| Var | Required | Description |
|---|---|---|
| `JWT_SECRET` | Yes | Random string for signing tokens (`openssl rand -hex 32`) |
| `USERNAME` | Yes | App login username |
| `PASSWORD` | Yes | App login password (plaintext) |
| `TAILSCALE_AUTHKEY` | Yes | Tailscale auth key (reusable + ephemeral) |
| `IBKR_HOST` | Yes | Home server's Tailscale IP (e.g. `100.64.x.x`) |
| `IBKR_PORT` | No | Default `4002` (paper) or `4001` (live) |
| `CORS_ORIGINS` | No | Comma-separated origins, defaults to localhost |
| `PORT` | No | Set automatically by Railway |

### Home server setup

```bash
# 1. Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# 2. Note your Tailscale IP
tailscale ip

# 3. Clone repo and configure gateway
git clone <repo-url> && cd trading_btc/gateway
cp .env.example .env
# Edit .env: set TWS_USERID, TWS_PASSWORD, TRADING_MODE

# 4. Start IB Gateway
docker compose up -d
```

## IBKR Setup Requirements

- IBKR account with **futures trading permissions**
- **CME market data subscription** (~$10-15/month non-professional)
- Start with **paper trading** (`TRADING_MODE=paper`) during development

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

## Local Development

```bash
# Backend
cd backend && pip install -r requirements.txt
cp .env.example .env  # edit with your settings
uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm install
npm run dev

# IB Gateway must be reachable at IBKR_HOST:IBKR_PORT
```

## API Endpoints

```
POST   /api/auth/login          → JWT token
GET    /api/positions            → current positions & P/L
POST   /api/order                → { side: "BUY"|"SELL" } (auto-max quantity)
POST   /api/close-position       → close any open MBT position
GET    /api/account              → account summary (balance, margin)
WS     /api/ws/candles           → streams 1-min candle updates
GET    /api/candles/history      → historical 1-min candles
```

## Key Files

- `RESEARCH.md` -- Regulatory research, cost analysis, why we chose IBKR + CME futures
- `Dockerfile` -- Multi-stage build: frontend + backend + Tailscale
- `start.sh` -- Container entrypoint: starts Tailscale then uvicorn
- `railway.json` -- Railway deployment config
- `gateway/docker-compose.yml` -- IB Gateway for home server
- `gateway/.env.example` -- Gateway env config template
- `backend/main.py` -- FastAPI app entry point
- `backend/ibkr.py` -- IBKR connection and trading logic via ib_insync
- `backend/models.py` -- Pydantic models
- `backend/.env.example` -- Backend env config template
- `frontend/src/App.tsx` -- Main app component
- `frontend/src/components/Chart.tsx` -- Candlestick chart
- `frontend/src/components/TradePanel.tsx` -- Long/Short/Close buttons
- `frontend/src/components/PositionBar.tsx` -- Position display with unrealized P/L
- `frontend/src/api.ts` -- Fetch wrapper with JWT auth, WebSocket helper
- `frontend/src/types.ts` -- TypeScript types matching backend models

## Development Notes

- Always develop against **paper trading** (port 4002) first
- Never commit secrets or auth tokens
- The backend must be running before the frontend can show live data
- IB Gateway disconnects after inactivity -- the backend handles reconnection
