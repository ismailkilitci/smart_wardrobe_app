from smartwardrobe_backend.api import create_app

import os

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    debug = os.getenv("DEBUG", "0").strip().lower() in {"1", "true", "yes"}
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=debug)
