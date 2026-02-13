import { useEffect, useState } from "react";
import { fetchPositions } from "../api";
import type { Position } from "../types";

export default function PositionBar({ refreshKey }: { refreshKey: number }) {
  const [positions, setPositions] = useState<Position[]>([]);

  const loadPositions = () => {
    fetchPositions()
      .then((data: { positions: Position[] }) => setPositions(data.positions))
      .catch(console.error);
  };

  useEffect(() => {
    loadPositions();
    const interval = setInterval(loadPositions, 5000);
    return () => clearInterval(interval);
  }, [refreshKey]);

  const pos = positions[0];

  if (!pos || pos.size === 0) {
    return (
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
        <p className="text-sm text-gray-500 text-center">No open position</p>
      </div>
    );
  }

  const isLong = pos.size > 0;
  const direction = isLong ? "LONG" : "SHORT";
  const dirColor = isLong ? "text-green-400" : "text-red-400";
  const pnlColor = pos.unrealized_pnl >= 0 ? "text-green-400" : "text-red-400";

  return (
    <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className={`font-bold ${dirColor}`}>{direction}</span>
          <span className="text-gray-300">{Math.abs(pos.size)} MBT</span>
          <span className="text-gray-500 text-sm">
            @ ${pos.avg_cost.toFixed(2)}
          </span>
        </div>
        <div className={`font-mono font-bold ${pnlColor}`}>
          {pos.unrealized_pnl >= 0 ? "+" : ""}${pos.unrealized_pnl.toFixed(2)}
        </div>
      </div>
    </div>
  );
}
