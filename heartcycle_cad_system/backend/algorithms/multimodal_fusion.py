"""
Compatibility shim — canonical source: ``app.algorithms.multimodal_fusion``.

This file is intentionally tiny. Any code still importing
``from algorithms.multimodal_fusion import ...`` (e.g. ``multimodal_service`` via
``importlib.spec_from_file_location`` or legacy scripts that put
``backend/`` first on ``sys.path``) gets the same symbols as the canonical
``app.algorithms.multimodal_fusion`` module.
"""
from app.algorithms.multimodal_fusion import *  # noqa: F401, F403
