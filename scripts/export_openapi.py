"""Generate contracts from local source without starting a server or connecting to the DB."""
import json
from pathlib import Path
from app.main import app

root = Path(__file__).resolve().parents[1]
(root / "apps/api/openapi.json").write_text(json.dumps(app.openapi(), indent=2) + "\n")
print("Exported API schema to apps/api/openapi.json")
