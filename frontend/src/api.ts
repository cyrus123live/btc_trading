const API_BASE = "/api";

function getToken(): string | null {
  return localStorage.getItem("token");
}

export function setToken(token: string) {
  localStorage.setItem("token", token);
}

export function clearToken() {
  localStorage.removeItem("token");
}

export function isAuthenticated(): boolean {
  return !!getToken();
}

async function authFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 401) {
    clearToken();
    window.location.reload();
  }
  return res;
}

export async function login(username: string, password: string): Promise<string> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    throw new Error("Invalid credentials");
  }
  const data = await res.json();
  setToken(data.access_token);
  return data.access_token;
}

export async function fetchPositions() {
  const res = await authFetch("/positions");
  if (!res.ok) throw new Error("Failed to fetch positions");
  return res.json();
}

export async function fetchAccount() {
  const res = await authFetch("/account");
  if (!res.ok) throw new Error("Failed to fetch account");
  return res.json();
}

export async function fetchCandleHistory(duration = "1 D", barSize = "1 min") {
  const params = new URLSearchParams({ duration, bar_size: barSize });
  const res = await authFetch(`/candles/history?${params}`);
  if (!res.ok) throw new Error("Failed to fetch candles");
  return res.json();
}

export async function placeOrder(side: "BUY" | "SELL") {
  const res = await authFetch("/order", {
    method: "POST",
    body: JSON.stringify({ side }),
  });
  if (!res.ok) throw new Error("Failed to place order");
  return res.json();
}

export async function closePosition() {
  const res = await authFetch("/close-position", { method: "POST" });
  if (!res.ok) throw new Error("Failed to close position");
  return res.json();
}

export function createCandleWebSocket(onMessage: (data: unknown) => void): WebSocket {
  const token = getToken();
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${protocol}//${window.location.host}${API_BASE}/ws/candles?token=${token}`);

  ws.onmessage = (event) => {
    const data = event.data;
    if (data === "heartbeat" || data === "pong") return;
    try {
      onMessage(JSON.parse(data));
    } catch {
      // ignore non-JSON messages
    }
  };

  // Keep alive
  const pingInterval = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send("ping");
    }
  }, 25000);

  ws.onclose = () => clearInterval(pingInterval);
  ws.onerror = () => clearInterval(pingInterval);

  return ws;
}
