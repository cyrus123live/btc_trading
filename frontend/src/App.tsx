import { useState } from "react";
import { isAuthenticated, clearToken } from "./api";
import Login from "./components/Login";
import Chart from "./components/Chart";
import TradePanel from "./components/TradePanel";
import PositionBar from "./components/PositionBar";

export default function App() {
  const [authed, setAuthed] = useState(isAuthenticated());
  const [refreshKey, setRefreshKey] = useState(0);

  if (!authed) {
    return <Login onLogin={() => setAuthed(true)} />;
  }

  return (
    <div className="max-w-5xl mx-auto p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold">BTC Trading</h1>
        <button
          onClick={() => { clearToken(); setAuthed(false); }}
          className="text-sm text-gray-500 hover:text-gray-300"
        >
          Logout
        </button>
      </div>

      <Chart />
      <PositionBar refreshKey={refreshKey} />
      <TradePanel onOrderPlaced={() => setRefreshKey((k) => k + 1)} />
    </div>
  );
}
