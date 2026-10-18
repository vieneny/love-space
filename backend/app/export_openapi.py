"""Regenerate backend/openapi.json from the real FastAPI route definitions."""
import json
from pathlib import Path
from .main import app

if __name__ == "__main__":
    target = Path(__file__).resolve().parent.parent / "openapi.json"
    target.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(target)
