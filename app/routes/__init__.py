from __future__ import annotations

import json
from pydantic import ValidationError


def format_validation_error(exc: ValidationError) -> list[dict]:
    """Return JSON-serializable validation errors."""
    return json.loads(exc.json(include_url=False))
