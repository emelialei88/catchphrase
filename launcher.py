"""PyInstaller entry point for Catchphrase.

Starts the FastAPI server, opens the user's browser, and keeps running
until quit. When frozen, static assets are loaded from sys._MEIPASS.
"""
import os
import sys
import socket
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn

# Pre-import so PyInstaller traces all dependencies of the app
# (uvicorn would otherwise load it lazily via importlib, after freezing).
import main as catchphrase_app  # noqa: F401


PORT = 7823
HOST = "127.0.0.1"
URL = f"http://{HOST}:{PORT}"


def find_open_port(preferred: int) -> int:
    """If preferred port is taken, fall back to OS-assigned port."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((HOST, preferred))
        s.close()
        return preferred
    except OSError:
        s.close()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((HOST, 0))
        port = s.getsockname()[1]
        s.close()
        return port


def open_browser_when_ready(url: str):
    """Poll the URL and open the browser once the server responds."""
    import urllib.request
    for _ in range(60):
        try:
            urllib.request.urlopen(url, timeout=0.5)
            webbrowser.open(url)
            return
        except Exception:
            time.sleep(0.3)
    # Fallback — open anyway after timeout
    webbrowser.open(url)


def main():
    # PyInstaller stores bundled data in sys._MEIPASS at runtime.
    if getattr(sys, "frozen", False):
        os.chdir(sys._MEIPASS)

    port = find_open_port(PORT)
    url = f"http://{HOST}:{port}"

    print(f"Catchphrase is running at {url}")
    print("Close this window to quit.")

    threading.Thread(target=open_browser_when_ready, args=(url,), daemon=True).start()

    uvicorn.run(catchphrase_app.app, host=HOST, port=port, log_level="warning")


if __name__ == "__main__":
    main()
