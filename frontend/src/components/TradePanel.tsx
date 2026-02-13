import { useState } from "react";
import { placeOrder, closePosition } from "../api";
import type { OrderResponse } from "../types";

export default function TradePanel({ onOrderPlaced }: { onOrderPlaced: () => void }) {
  const [loading, setLoading] = useState<"BUY" | "SELL" | "CLOSE" | null>(null);
  const [lastOrder, setLastOrder] = useState<OrderResponse | null>(null);

  const handleOrder = async (side: "BUY" | "SELL") => {
    setLoading(side);
    try {
      const result = await placeOrder(side);
      setLastOrder(result);
      onOrderPlaced();
    } catch (err) {
      console.error("Order failed:", err);
    } finally {
      setLoading(null);
    }
  };

  const handleClose = async () => {
    setLoading("CLOSE");
    try {
      const result = await closePosition();
      setLastOrder(result);
      onOrderPlaced();
    } catch (err) {
      console.error("Close position failed:", err);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="bg-gray-900 rounded-lg p-4 space-y-4 border border-gray-800">
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">Trade MBT</h2>

      <div className="flex gap-3">
        <button
          onClick={() => handleOrder("BUY")}
          disabled={loading !== null}
          className="flex-1 py-3 bg-green-600 hover:bg-green-700 rounded-lg font-bold text-lg disabled:opacity-50 transition-colors"
        >
          {loading === "BUY" ? "..." : "Long"}
        </button>
        <button
          onClick={handleClose}
          disabled={loading !== null}
          className="flex-1 py-3 bg-gray-600 hover:bg-gray-700 rounded-lg font-bold text-lg disabled:opacity-50 transition-colors"
        >
          {loading === "CLOSE" ? "..." : "Close"}
        </button>
        <button
          onClick={() => handleOrder("SELL")}
          disabled={loading !== null}
          className="flex-1 py-3 bg-red-600 hover:bg-red-700 rounded-lg font-bold text-lg disabled:opacity-50 transition-colors"
        >
          {loading === "SELL" ? "..." : "Short"}
        </button>
      </div>

      {lastOrder && (
        <div className="text-xs text-gray-500 text-center">
          Last: {lastOrder.side} {lastOrder.quantity} @ {lastOrder.avg_fill_price ?? "pending"}{" "}
          ({lastOrder.status})
        </div>
      )}
    </div>
  );
}
