# Quick Start Guide

## One-time setup (2 minutes)

```bash
# Install Ollama (if not already)
# Windows: download from https://ollama.com
# macOS: brew install ollama
# Linux: curl -fsSL https://ollama.com/install.sh | sh

# Pull the model
ollama pull llama3

# Set up the project
cd "interview v2"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Run the simulator
python main.py
```

## Run tests

```bash
python -m pytest -v
```

## That's it.

The simulator will guide you through the rest interactively.
