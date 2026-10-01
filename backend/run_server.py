"""
run_server.py

Starts the FastAPI backend server using Uvicorn.

Usage:
    python backend/run_server.py
"""

import sys
from pathlib import Path
import uvicorn

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import API_HOST, API_PORT

if __name__ == "__main__":
    print(f"Starting Satellite Change Detection API at http://{API_HOST}:{API_PORT}")
    uvicorn.run("app.main:app", host=API_HOST, port=API_PORT, reload=True)
