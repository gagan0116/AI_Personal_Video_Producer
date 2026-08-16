#!/usr/bin/env bash
set -e

echo "================================================================="
echo "⚡ Acer Veriton GN100 DGX Spark Setup for AI Sports Producer"
echo "================================================================="

# 1. System checks
echo "[1/6] Checking NVIDIA GPU and Driver..."
nvidia-smi

echo "[2/6] Verifying Docker and NVIDIA Container Toolkit..."
docker --version
docker compose version

# 3. Install system dependencies
echo "[3/6] Installing OS utilities and FFmpeg..."
sudo apt-get update -y
sudo apt-get install -y ffmpeg python3-pip python3-venv git curl unzip

# 4. Setup Python Virtual Environment
echo "[4/6] Setting up Python 3 environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. Create cache and output directories
echo "[5/6] Creating local cache and output directories..."
mkdir -p ~/.cache/nim
mkdir -p output/fan output/coach output/social

# 6. Install NemoClaw CLI & OpenShell
echo "[6/6] Installing NVIDIA NemoClaw and OpenShell..."
if ! command -v openshell &> /dev/null; then
    curl -LsSf https://raw.githubusercontent.com/NVIDIA/OpenShell/main/install.sh | sh || true
fi

if ! command -v nemoclaw &> /dev/null; then
    curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash || true
fi

echo "================================================================="
echo "✅ GN100 Environment setup complete!"
echo "Next step: run ./scripts/start.sh to launch the application."
echo "================================================================="
