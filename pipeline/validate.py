#!/usr/bin/env python3
"""Validate data/seed/*.json files against schema/deal.schema.json."""

import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    print("Error: jsonschema not installed. Run: pip install jsonschema", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).parent.parent
SCHEMA_PATH = ROOT / "schema" / "deal.schema.json"
SEED_DIR = ROOT / "data" / "seed"


def main() -> int:
    schema = json.loads(SCHEMA_PATH.read_text())
    files = sorted(SEED_DIR.glob("*.json"))

    if not files:
        print("No seed files found in data/seed/")
        return 0

    errors = []
    for path in files:
        try:
            record = json.loads(path.read_text())
            jsonschema.validate(instance=record, schema=schema)
            print(f"  OK  {path.name}")
        except json.JSONDecodeError as e:
            errors.append((path.name, f"JSON parse error: {e}"))
            print(f"  FAIL {path.name}: JSON parse error: {e}")
        except jsonschema.ValidationError as e:
            errors.append((path.name, e.message))
            print(f"  FAIL {path.name}: {e.message}")

    print(f"\n{len(files) - len(errors)}/{len(files)} passed")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
