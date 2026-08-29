"""Boots a throwaway API server for the Playwright E2E suite.

Creates a temp SQLite DB (never touches the dev DB), seeds the demo accounts,
stubs the LLM boundary so tests are deterministic without Ollama/OpenAI, then
serves the real FastAPI app. Target of the `webServer` entry in the Playwright
config.

Usage (from repo root, venv active):
    venv\\Scripts\\python backend\\scripts\\e2e_server.py
"""

import json
import os
import sys
import tempfile
import unittest.mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Point the app at a throwaway DB BEFORE importing anything from backend.app.
fd, _db = tempfile.mkstemp(prefix="e2e_", suffix=".db")
os.close(fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_db}"
os.environ.setdefault("ENV", "development")


def _mock_llm(messages, *args, **kwargs):
    return {
        "message": {
            "content": json.dumps(
                {
                    "relevance": 7.2,
                    "clarity": 7.0,
                    "creativity": 6.8,
                    "communication": 7.5,
                    "overall_score": 7.1,
                    "strengths": ["Clear structure", "Concrete example"],
                    "weaknesses": ["Could quantify the impact"],
                    "ideal_answer": "",
                    "follow_up": "Can you quantify the impact of what you described?",
                    "is_serious": True,
                    "score": 8,
                }
            )
        }
    }


def main():
    import uvicorn

    from backend.app import app  # create_all + routers
    from backend.app.db.database import SessionLocal
    from backend.scripts.seed_dev import _upsert_accounts

    with SessionLocal() as session:
        _upsert_accounts(session)

    unittest.mock.patch("core.evaluator._call_llm", side_effect=_mock_llm).start()
    unittest.mock.patch(
        "core.engine.pre_screen_answer", return_value={"pass": True, "auto_score": 0}
    ).start()

    print(f"[e2e_server] temp DB: {_db}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


if __name__ == "__main__":
    main()