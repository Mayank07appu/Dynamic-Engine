"""PulseRide Application Entry Point.
Run with: python main.py
"""

import sys
import uvicorn

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def run():
    print("=" * 65)
    print("🚀 Starting PulseRide Dynamic Pricing Engine...")
    print("🌐 Dashboard UI:       http://127.0.0.1:8000")
    print("📚 API Documentation:  http://127.0.0.1:8000/docs")
    print("⚡ Health Status:      http://127.0.0.1:8000/api/v1/health")
    print("=" * 65)
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    run()
