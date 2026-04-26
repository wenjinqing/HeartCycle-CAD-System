"""
Compatibility shim — canonical source: ``app.algorithms.multimodal_ablation``.

This file is intentionally tiny. Any code still importing
``from algorithms.multimodal_ablation import ...`` (e.g. ``multimodal_service`` via
``importlib.spec_from_file_location`` or legacy scripts that put
``backend/`` first on ``sys.path``) gets the same symbols as the canonical
``app.algorithms.multimodal_ablation`` module.
"""
from app.algorithms.multimodal_ablation import *  # noqa: F401, F403
