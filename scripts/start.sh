#!/usr/bin/env bash
set -e

echo "================================================================="
echo "🏟️ Starting Personal AI Sports Producer on Acer GN100"
echo "================================================================="

# Activate virtual environment if present
if [ -d "venv" ]; then
    source venv/bin/activate
fi

export PYTHONPATH="."
export HOST="0.0.0.0"
export PORT="8080"

# Launch FastAPI with Uvicorn
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
