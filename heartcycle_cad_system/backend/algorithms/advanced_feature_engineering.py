"""
Compatibility shim — canonical source: ``app.algorithms.advanced_feature_engineering``.

This file is intentionally tiny. Any code still importing
``from algorithms.advanced_feature_engineering import ...`` (e.g. ``multimodal_service`` via
``importlib.spec_from_file_location`` or legacy scripts that put
``backend/`` first on ``sys.path``) gets the same symbols as the canonical
``app.algorithms.advanced_feature_engineering`` module.
"""
from app.algorithms.advanced_feature_engineering import *  # noqa: F401, F403
