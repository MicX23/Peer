import sys
import uvicorn
from electron_app import create_app

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: core <port>")
        sys.exit(1)

    try:
        port = int(sys.argv[1])
    except ValueError:
        print("Port must be a number")
        sys.exit(1)

    if not (1 <= port <= 65535):
        print("Port must be between 1 and 65535")
        sys.exit(1)
    uvicorn.run(
        create_app(),          # ← Node создастся внутри lifespan
        host="127.0.0.1",
        port=port,
        log_level="info",
        ws="websockets",
    )