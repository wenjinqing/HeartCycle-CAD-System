"""
Compatibility shim — canonical source: ``app.algorithms.deep_learning``.

This file is intentionally tiny. Any code still importing
``from algorithms.deep_learning import ...`` (e.g. ``multimodal_service`` via
``importlib.spec_from_file_location`` or legacy scripts that put
``backend/`` first on ``sys.path``) gets the same symbols as the canonical
``app.algorithms.deep_learning`` module.
"""
from app.algorithms.deep_learning import *  # noqa: F401, F403
