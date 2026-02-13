export interface Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Position {
  symbol: string;
  size: number;
  avg_cost: number;
  unrealized_pnl: number;
  market_value: number;
}

export interface OrderResponse {
  order_id: number;
  side: string;
  quantity: number;
  status: string;
  avg_fill_price: number | null;
}

export interface AccountSummary {
  net_liquidation: number;
  available_funds: number;
  buying_power: number;
  margin_used: number;
}
