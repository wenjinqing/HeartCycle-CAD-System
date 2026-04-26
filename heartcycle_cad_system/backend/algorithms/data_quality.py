"""
Compatibility shim — canonical source: ``app.algorithms.data_quality``.

This file is intentionally tiny. Any code still importing
``from algorithms.data_quality import ...`` (e.g. ``multimodal_service`` via
``importlib.spec_from_file_location`` or legacy scripts that put
``backend/`` first on ``sys.path``) gets the same symbols as the canonical
``app.algorithms.data_quality`` module.
"""
from app.algorithms.data_quality import *  # noqa: F401, F403
