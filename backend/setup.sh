#!/usr/bin/env bash
# setup.sh — one-time backend environment setup
set -e

echo "==> Smart Study Reminder AI — Backend Setup"
echo "==> Python: $(python --version 2>&1)"

# Create virtual environment
python -m venv venv
echo "==> Virtual environment created at ./venv"

# Activate and install dependencies
source venv/bin/activate || . venv/Scripts/activate

pip install --upgrade pip
pip install -r requirements.txt
echo "==> Dependencies installed"

# Copy .env if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "==> .env created from .env.example — please fill in your real values"
fi

echo ""
echo "✅ Setup complete. Run ./run.sh to start the backend."
