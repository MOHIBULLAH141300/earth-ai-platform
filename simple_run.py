#!/usr/bin/env python3
"""
Simple startup script - just run Streamlit with API built-in
"""
import subprocess
import sys

def main():
    print("🌍 Starting EarthAI Platform...")
    print("🎨 Streamlit Dashboard with Built-in API")
    print("=" * 50)
    
    try:
        # Run Streamlit only - it will handle the UI
        subprocess.run([
            "streamlit", 
            "run", 
            "app_visual.py", 
            "--server.port", "10000",
            "--server.address", "0.0.0.0",
            "--server.headless", "true"
        ], check=True)
    except Exception as e:
        print(f"❌ Failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
