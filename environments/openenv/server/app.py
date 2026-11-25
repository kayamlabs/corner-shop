"""FastAPI application for the Corner Shop environment.

Endpoints (from openenv-core):
    POST /reset, POST /step, GET /state, GET /schema, GET /metadata, GET /health, WS /ws

The HTTP /reset and /step endpoints are stateless (a fresh simulator per request), so a full
episode needs the WebSocket session that CornerShopEnv (client.py) opens.

Usage:
    uvicorn server.app:app --host 0.0.0.0 --port 8000
    python -m server.app --port 8000
"""
import os

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:  # pragma: no cover
    raise ImportError("openenv-core is required. Install dependencies with 'uv sync'.") from e

try:
    from ..models import CornerShopAction, CornerShopObservation
    from .corner_shop_environment import CornerShopEnvironment
except ImportError:
    from models import CornerShopAction, CornerShopObservation
    from server.corner_shop_environment import CornerShopEnvironment


app = create_app(
    CornerShopEnvironment,
    CornerShopAction,
    CornerShopObservation,
    env_name="corner_shop",
    max_concurrent_envs=int(os.environ.get("MAX_CONCURRENT_ENVS", "16")),
)


def main(host: str = "0.0.0.0", port: int = 8000):
    """Run the server: `uv run --project . server` or `python -m server.app`."""
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    main(host=args.host, port=args.port)
