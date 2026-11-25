"""Corner Shop ORS server. Run `sh build.sh` once, then `python server.py` (listens on :8080)."""
from openreward.environments import Server

from corner_shop import CornerShop

if __name__ == "__main__":
    Server([CornerShop]).run()
