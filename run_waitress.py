import os
import sys
from pathlib import Path
from waitress import serve
from config.wsgi import application

# Base project directory
BASE_DIR = Path(__file__).resolve().parent

if __name__ == "__main__":
    host = os.environ.get("SANADBAN_HOST", "127.0.0.1")
    port = int(os.environ.get("SANADBAN_PORT", "8000"))
    threads = int(os.environ.get("SANADBAN_THREADS", "8"))

    print("=" * 65)
    print("       SanadBan (MaskanYar) Production WSGI Server")
    print(f"       Binding on     : http://{host}:{port}")
    print(f"       Worker Threads : {threads}")
    print(f"       Project Root   : {BASE_DIR}")
    print("=" * 65)

    serve(
        application,
        host=host,
        port=port,
        threads=threads,
        channel_timeout=90,
        cleanup_interval=30,
        max_request_body_size=104857600,  # 100 MB for large scan attachments
    )
