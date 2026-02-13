import { useState } from "react";
import { placeOrder } from "../api";
import type { OrderResponse } from "../types";

export default function TradePanel({ onOrderPlaced }: { onOrderPlaced: () => void }) {
  const [quantity, setQuantity] = useState(1);
  const [loading, setLoading] = useState<"BUY" | "SELL" | null>(null);
  const [lastOrder, setLastOrder] = useState<OrderResponse | null>(null);

  const handleOrder = async (side: "BUY" | "SELL") => {
    setLoading(side);
    try {
      const result = await placeOrder(side, quantity);
      setLastOrder(result);
      onOrderPlaced();
    } catch (err) {
      console.error("Order failed:", err);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="bg-gray-900 rounded-lg p-4 space-y-4 border border-gray-800">
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">Trade MBT</h2>

      <div className="flex items-center gap-3">
        <label className="text-sm text-gray-400">Qty:</label>
        <input
          type="number"
          min={1}
          max={10}
          value={quantity}
          onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
          className="w-20 px-2 py-1 bg-gray-800 rounded border border-gray-700 text-center focus:border-blue-500 focus:outline-none"
        />
      </div>

      <div className="flex gap-3">
        <button
          onClick={() => handleOrder("BUY")}
          disabled={loading !== null}
          className="flex-1 py-3 bg-green-600 hover:bg-green-700 rounded-lg font-bold text-lg disabled:opacity-50 transition-colors"
        >
          {loading === "BUY" ? "..." : "Long"}
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
