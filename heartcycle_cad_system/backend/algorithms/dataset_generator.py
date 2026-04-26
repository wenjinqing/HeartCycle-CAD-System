"""
Compatibility shim — canonical source: ``app.algorithms.dataset_generator``.

This file is intentionally tiny. Any code still importing
``from algorithms.dataset_generator import ...`` (e.g. ``multimodal_service`` via
``importlib.spec_from_file_location`` or legacy scripts that put
``backend/`` first on ``sys.path``) gets the same symbols as the canonical
``app.algorithms.dataset_generator`` module.
"""
from app.algorithms.dataset_generator import *  # noqa: F401, F403
