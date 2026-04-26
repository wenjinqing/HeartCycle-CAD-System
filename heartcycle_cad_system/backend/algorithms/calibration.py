"""
Compatibility shim — canonical source: ``app.algorithms.calibration``.

This file is intentionally tiny. Any code still importing
``from algorithms.calibration import ...`` (e.g. ``multimodal_service`` via
``importlib.spec_from_file_location`` or legacy scripts that put
``backend/`` first on ``sys.path``) gets the same symbols as the canonical
``app.algorithms.calibration`` module.
"""
from app.algorithms.calibration import *  # noqa: F401, F403
