from __future__ import annotations

import os
import sys
from pathlib import Path


# Allow running this file from either:
# - repo root: `python backend/app.py`
# - backend dir: `python app.py`
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


from backend.smartwardrobe_backend.api import create_app

app = create_app()

if __name__ == "__main__":
    print("Starting Smart Wardrobe Backend (Flask)...")
    print("- Health:          GET  /health")
    print("- Wardrobe upload: POST /wardrobe/items")
    print("- Wardrobe list:   GET  /wardrobe/items")
    print("- Recommend:       POST /recommendations")
    debug = os.getenv("DEBUG", "1").strip().lower() not in ("0", "false", "no")
    port = int(os.getenv("PORT", "5000"))
    # Avoid reloader for more deterministic behavior in dev scripts.
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)
