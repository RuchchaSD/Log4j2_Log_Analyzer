#!/usr/bin/env python3
"""Entry point: launches the WSO2 Log Analyzer server."""
import uvicorn
import webbrowser
import threading
import time


def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://localhost:8765")


if __name__ == "__main__":
    t = threading.Thread(target=open_browser, daemon=True)
    t.start()
    uvicorn.run(
        "server.app:app",
        host="0.0.0.0",
        port=8765,
        reload=True,
        log_level="info",
    )
