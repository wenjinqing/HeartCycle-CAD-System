"""
Compatibility shim — canonical source: ``app.algorithms.feature_analysis``.

This file is intentionally tiny. Any code still importing
``from algorithms.feature_analysis import ...`` (e.g. ``multimodal_service`` via
``importlib.spec_from_file_location`` or legacy scripts that put
``backend/`` first on ``sys.path``) gets the same symbols as the canonical
``app.algorithms.feature_analysis`` module.
"""
from app.algorithms.feature_analysis import *  # noqa: F401, F403
