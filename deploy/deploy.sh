#!/bin/bash
# =============================================================================
# ImmersiveRAG — EC2 Deployment Script
# Ubuntu 24.04 LTS | Single-instance POC
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh
#
# What this does:
#   1. Installs system dependencies (Python 3.11, Node 20, Nginx)
#   2. Sets up the Python venv and installs backend packages
#   3. Builds the Next.js frontend
#   4. Installs systemd services for backend + frontend
#   5. Configures Nginx as reverse proxy on port 80
#   6. Starts everything and enables auto-start on reboot
# =============================================================================

set -e  # Exit immediately on any error

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY_DIR="$REPO_DIR/deploy"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║         ImmersiveRAG EC2 Deployment Script           ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "→ Repo root: $REPO_DIR"
echo ""

# ── 1. System dependencies ────────────────────────────────────────────────────
echo "[1/6] Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    build-essential \
    nginx \
    git \
    curl

# Install Node.js 20 via NodeSource if not already installed
if ! command -v node &>/dev/null || [[ "$(node -v)" != v20* ]]; then
    echo "      Installing Node.js 20..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - -qq
    sudo apt-get install -y -qq nodejs
fi

echo "      Python: $(python3.11 --version)"
echo "      Node:   $(node --version)"
echo "      npm:    $(npm --version)"

# ── 2. Backend: Python venv + dependencies ────────────────────────────────────
echo ""
echo "[2/6] Setting up Python virtual environment..."
cd "$REPO_DIR"

if [ ! -d "backend/.venv" ]; then
    python3.11 -m venv backend/.venv
    echo "      Created new venv at backend/.venv"
fi

source backend/.venv/bin/activate
pip install --upgrade pip -q
pip install -e "backend[dev]" -q
pip install langgraph -q
deactivate

echo "      Backend dependencies installed."

# ── 3. Backend: .env file ─────────────────────────────────────────────────────
echo ""
echo "[3/6] Checking backend .env..."
if [ ! -f "backend/.env" ]; then
    cp backend/.env.example backend/.env
    echo ""
    echo "  ⚠️  Created backend/.env from .env.example"
    echo "  ⚠️  You MUST edit backend/.env and fill in your credentials before starting."
    echo "      Run: nano backend/.env"
    echo ""
else
    echo "      backend/.env already exists — skipping."
fi

# ── 4. Frontend: install + build ──────────────────────────────────────────────
echo ""
echo "[4/6] Building Next.js frontend..."
cd "$REPO_DIR/frontend"
npm install --silent
npm run build
echo "      Frontend build complete."

# ── 5. Systemd services ───────────────────────────────────────────────────────
echo ""
echo "[5/6] Installing systemd services..."

# Substitute the actual repo path into the service files
sed "s|/home/ubuntu/immersiveRAG|$REPO_DIR|g" \
    "$DEPLOY_DIR/immersiverag-backend.service" \
    | sudo tee /etc/systemd/system/immersiverag-backend.service > /dev/null

sed "s|/home/ubuntu/immersiveRAG|$REPO_DIR|g" \
    "$DEPLOY_DIR/immersiverag-frontend.service" \
    | sudo tee /etc/systemd/system/immersiverag-frontend.service > /dev/null

# Fix the node path in the frontend service to use the actual node binary
NODE_PATH="$(which node)"
sudo sed -i "s|/usr/bin/node|$NODE_PATH|g" /etc/systemd/system/immersiverag-frontend.service

# Set the current user in the service files
CURRENT_USER="$(whoami)"
sudo sed -i "s|User=ubuntu|User=$CURRENT_USER|g" /etc/systemd/system/immersiverag-backend.service
sudo sed -i "s|User=ubuntu|User=$CURRENT_USER|g" /etc/systemd/system/immersiverag-frontend.service

sudo systemctl daemon-reload
sudo systemctl enable immersiverag-backend immersiverag-frontend
echo "      Services installed and enabled."

# ── 6. Nginx configuration ────────────────────────────────────────────────────
echo ""
echo "[6/6] Configuring Nginx..."
sudo cp "$DEPLOY_DIR/nginx.conf" /etc/nginx/sites-available/immersiverag
sudo ln -sf /etc/nginx/sites-available/immersiverag /etc/nginx/sites-enabled/immersiverag
# Remove default site to avoid conflicts
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl enable nginx
echo "      Nginx configured."

# ── Start everything ──────────────────────────────────────────────────────────
echo ""
echo "Starting services..."
sudo systemctl restart immersiverag-backend
sleep 3
sudo systemctl restart immersiverag-frontend
sleep 3
sudo systemctl restart nginx

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║                  Deployment Complete!                ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "Service status:"
sudo systemctl is-active immersiverag-backend  && echo "  ✓ Backend  (port 8000) — running" || echo "  ✗ Backend  — FAILED (check: journalctl -u immersiverag-backend -n 50)"
sudo systemctl is-active immersiverag-frontend && echo "  ✓ Frontend (port 3000) — running" || echo "  ✗ Frontend — FAILED (check: journalctl -u immersiverag-frontend -n 50)"
sudo systemctl is-active nginx                 && echo "  ✓ Nginx    (port 80)   — running" || echo "  ✗ Nginx    — FAILED"

echo ""
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "<your-ec2-public-ip>")
echo "  → App is live at: http://$PUBLIC_IP"
echo ""
echo "Useful commands:"
echo "  View backend logs:  journalctl -u immersiverag-backend -f"
echo "  View frontend logs: journalctl -u immersiverag-frontend -f"
echo "  Restart backend:    sudo systemctl restart immersiverag-backend"
echo "  Restart frontend:   sudo systemctl restart immersiverag-frontend"
echo "  Edit .env:          nano $REPO_DIR/backend/.env"
echo ""
