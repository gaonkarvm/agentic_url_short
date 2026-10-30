#!/bin/bash
set -e

echo "=========================================="
echo "Setting up Agentic URL Shortener Environment"
echo "=========================================="

# 1. Check Python version
python3 --version

# 2. Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment (.venv)..."
    python3 -m venv .venv
fi

# 3. Activate virtual environment and upgrade pip
echo "Upgrading pip in virtual environment..."
./.venv/bin/pip install --upgrade pip

# 4. Install dependencies
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    ./.venv/bin/pip install -r requirements.txt
else
    echo "requirements.txt not found! Installing core packages manually..."
    ./.venv/bin/pip install fastapi uvicorn redis pydantic langchain-openai langchain-core pytest
fi

# 5. Ensure workspace directory exists
mkdir -p workspace

echo "=========================================="
echo "Setup complete! Run the system using:"
echo "source .venv/bin/activate && python main.py"
echo "=========================================="