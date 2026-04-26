"""
Compatibility shim — canonical source: ``app.algorithms.automl``.

This file is intentionally tiny. Any code still importing
``from algorithms.automl import ...`` (e.g. ``multimodal_service`` via
``importlib.spec_from_file_location`` or legacy scripts that put
``backend/`` first on ``sys.path``) gets the same symbols as the canonical
``app.algorithms.automl`` module.
"""
from app.algorithms.automl import *  # noqa: F401, F403
