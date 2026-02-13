import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from ibkr import IBKRClient
from models import (
    AuthRequest,
    TokenResponse,
    OrderRequest,
    OrderResponse,
    Candle,
)

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
IBKR_HOST = os.getenv("IBKR_HOST", "127.0.0.1")
IBKR_PORT = int(os.getenv("IBKR_PORT", "4002"))
IBKR_CLIENT_ID = int(os.getenv("IBKR_CLIENT_ID", "1"))
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
USERNAME = os.getenv("USERNAME", "admin")
PASSWORD = os.getenv("PASSWORD", "")

# IBKR client singleton
ibkr = IBKRClient(host=IBKR_HOST, port=IBKR_PORT, client_id=IBKR_CLIENT_ID)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        await ibkr.connect()
        await ibkr.qualify_contract()
        logger.info("IBKR connected and contract qualified")
    except Exception as e:
        logger.warning(f"Could not connect to IBKR on startup: {e}")
        logger.warning("Start IB Gateway and the app will reconnect on first request")
    yield
    # Shutdown
    await ibkr.disconnect()


app = FastAPI(title="BTC Trading Bot", lifespan=lifespan)

cors_origins = os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()


# --- Auth ---

def create_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    return jwt.encode({"sub": username, "exp": expire}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(req: AuthRequest):
    if req.username != USERNAME:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not PASSWORD or req.password != PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(req.username)
    return TokenResponse(access_token=token)


# --- REST Endpoints ---

@app.get("/api/positions")
async def get_positions(user: str = Depends(verify_token)):
    try:
        positions = await ibkr.get_positions()
        return {"positions": [p.model_dump() for p in positions]}
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/order", response_model=OrderResponse)
async def place_order(req: OrderRequest, user: str = Depends(verify_token)):
    if req.side.upper() not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="Side must be BUY or SELL")
    try:
        result = await ibkr.place_max_order(req.side)
        return OrderResponse(**result)
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/close-position", response_model=OrderResponse)
async def close_position(user: str = Depends(verify_token)):
    try:
        result = await ibkr.close_position()
        return OrderResponse(**result)
    except Exception as e:
        logger.error(f"Error closing position: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/account")
async def get_account(user: str = Depends(verify_token)):
    try:
        summary = await ibkr.get_account_summary()
        return summary.model_dump()
    except Exception as e:
        logger.error(f"Error getting account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/candles/history")
async def get_candle_history(
    duration: str = "1 D",
    bar_size: str = "1 min",
    user: str = Depends(verify_token),
):
    try:
        candles = await ibkr.get_historical_candles(duration, bar_size)
        return {"candles": [c.model_dump() for c in candles]}
    except Exception as e:
        logger.error(f"Error getting candles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- WebSocket ---

@app.websocket("/api/ws/candles")
async def ws_candles(ws: WebSocket):
    await ws.accept()
    # Verify token from query param
    token = ws.query_params.get("token")
    if not token:
        await ws.close(code=4001, reason="Missing token")
        return
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if not payload.get("sub"):
            await ws.close(code=4001, reason="Invalid token")
            return
    except JWTError:
        await ws.close(code=4001, reason="Invalid token")
        return

    logger.info("WebSocket client connected for candle streaming")

    # Aggregate 5-second bars into 1-minute candles
    current_candle: dict | None = None
    candle_minute: int = -1

    async def on_bar_update(bars, hasNewBar):
        nonlocal current_candle, candle_minute
        if not hasNewBar or not bars:
            return
        bar = bars[-1]
        bar_time = bar.time if hasattr(bar, "time") else bar.date
        if isinstance(bar_time, datetime):
            ts = int(bar_time.timestamp())
        else:
            ts = int(bar_time)
        minute = ts // 60

        if minute != candle_minute:
            # Emit completed candle
            if current_candle is not None:
                try:
                    await ws.send_json(current_candle)
                except Exception:
                    return
            # Start new candle
            candle_minute = minute
            current_candle = {
                "time": minute * 60,
                "open": bar.open_,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume if hasattr(bar, "volume") else 0,
            }
        else:
            # Update current candle
            if current_candle is not None:
                current_candle["high"] = max(current_candle["high"], bar.high)
                current_candle["low"] = min(current_candle["low"], bar.low)
                current_candle["close"] = bar.close
                current_candle["volume"] = current_candle.get("volume", 0) + (
                    bar.volume if hasattr(bar, "volume") else 0
                )

    realtime_bars = None
    try:
        realtime_bars = await ibkr.subscribe_realtime_bars(on_bar_update)
        # Keep connection alive
        while True:
            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=30)
                if msg == "ping":
                    await ws.send_text("pong")
            except asyncio.TimeoutError:
                # Send heartbeat
                try:
                    await ws.send_text("heartbeat")
                except Exception:
                    break
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if realtime_bars is not None:
            ibkr.ib.cancelRealTimeBars(realtime_bars)


# --- Static file serving (production: built frontend) ---

STATIC_DIR = Path(__file__).parent / "static"

if STATIC_DIR.is_dir():

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve built frontend files, falling back to index.html for SPA routing."""
        file = STATIC_DIR / full_path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(STATIC_DIR / "index.html")
