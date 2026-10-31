import os
import sys
from pathlib import Path
from waitress import serve
from config.wsgi import application

# Base project directory
BASE_DIR = Path(__file__).resolve().parent

if __name__ == "__main__":
    # Check CLI argument for port (e.g. python run_waitress.py 8005)
    cli_port = None
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        cli_port = int(sys.argv[1])

    host = os.environ.get("SANADBAN_HOST", "127.0.0.1")
    port = cli_port or int(os.environ.get("SANADBAN_PORT", "8005"))
    threads = int(os.environ.get("SANADBAN_THREADS", "16"))

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
        channel_timeout=180,
        cleanup_interval=30,
        connection_limit=1000,
        backlog=2048,
        max_request_body_size=104857600,  # 100 MB for large scan attachments
    )
