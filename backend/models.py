from pydantic import BaseModel
from typing import Optional


class Candle(BaseModel):
    time: int  # unix timestamp
    open: float
    high: float
    low: float
    close: float
    volume: float = 0


class OrderRequest(BaseModel):
    side: str  # "BUY" or "SELL"
    quantity: int = 1


class OrderResponse(BaseModel):
    order_id: int
    side: str
    quantity: int
    status: str
    avg_fill_price: Optional[float] = None


class Position(BaseModel):
    symbol: str
    size: float  # positive = long, negative = short
    avg_cost: float
    unrealized_pnl: float
    market_value: float


class AccountSummary(BaseModel):
    net_liquidation: float
    available_funds: float
    buying_power: float
    margin_used: float


class AuthRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
