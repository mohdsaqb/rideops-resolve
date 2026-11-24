"""Start the same web app from a local checkout or the Docker image."""

import errno
import os
from pathlib import Path
import socket

from alembic import command
from alembic.config import Config
import uvicorn

from .import_csv import run as import_tickets
from .main import app, web_dir


def main():
    if not (web_dir / "index.html").is_file():
        raise SystemExit(
            "The interface is missing. Build it with the local launcher or the root Dockerfile."
        )
    command.upgrade(Config(str(Path(__file__).resolve().parents[1] / "alembic.ini")), "head")
    print(f"Imported {import_tickets()} tickets", flush=True)
    host = os.getenv("HOST", "127.0.0.1")
    try:
        port = int(os.getenv("PORT", "3000"))
        if not 0 <= port <= 65535:
            raise ValueError
    except ValueError:
        raise SystemExit("PORT must be a number from 0 to 65535.") from None
    try:
        listener = socket.create_server((host, port))
    except OSError as error:
        if error.errno != errno.EADDRINUSE or host != "127.0.0.1" or "PORT" in os.environ:
            raise
        listener = socket.create_server((host, 0))
    with listener:
        address = listener.getsockname()[1]
        if host == "127.0.0.1":
            print(f"Open http://127.0.0.1:{address}  ·  Ctrl+C to stop", flush=True)
        uvicorn.Server(uvicorn.Config(app, host=host, port=address)).run(sockets=[listener])


if __name__ == "__main__":
    try:
        main()
    except OSError as error:
        raise SystemExit(f"Could not start RideOps: {error}") from None
