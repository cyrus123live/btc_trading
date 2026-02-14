#!/bin/sh
set -e

# Start Tailscale daemon in userspace mode (no TUN device needed in containers)
tailscaled --tun=userspace-networking --state=/var/lib/tailscale/tailscaled.state &

# Wait for tailscaled to be ready
sleep 2

# Authenticate and connect to tailnet
tailscale up --authkey="${TAILSCALE_AUTHKEY}" --hostname=railway-btc-trading

# Wait for Tailscale to establish connection
sleep 3

echo "Tailscale status:"
tailscale status

# Start the app
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
