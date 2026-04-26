#!/usr/bin/env python3
"""
Startup script to run both FastAPI backend and Streamlit frontend
"""
import subprocess
import threading
import time
import os
import sys

def run_fastapi():
    """Run FastAPI backend on port 8000"""
    try:
        print("🚀 Starting FastAPI backend on port 8000...")
        subprocess.run([
            "uvicorn", 
            "main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000",
            "--workers", "1"
        ], check=True)
    except Exception as e:
        print(f"❌ FastAPI failed to start: {e}")
        sys.exit(1)

def run_streamlit():
    """Run Streamlit frontend on port 10000"""
    try:
        print("🎨 Starting Streamlit frontend on port 10000...")
        # Wait a bit for FastAPI to start
        time.sleep(5)
        subprocess.run([
            "streamlit", 
            "run", 
            "app_visual.py", 
            "--server.port", "10000",
            "--server.address", "0.0.0.0"
        ], check=True)
    except Exception as e:
        print(f"❌ Streamlit failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🌍 Starting EarthAI Platform...")
    print("🚀 Backend: FastAPI on port 8000")
    print("🎨 Frontend: Streamlit on port 10000")
    print("=" * 50)
    
    # Start FastAPI in background thread
    fastapi_thread = threading.Thread(target=run_fastapi, daemon=True)
    fastapi_thread.start()
    
    # Start Streamlit in main thread
    run_streamlit()
