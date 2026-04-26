"""
Compatibility shim — canonical source: ``app.algorithms.experiment_evaluation``.

This file is intentionally tiny. Any code still importing
``from algorithms.experiment_evaluation import ...`` (e.g. ``multimodal_service`` via
``importlib.spec_from_file_location`` or legacy scripts that put
``backend/`` first on ``sys.path``) gets the same symbols as the canonical
``app.algorithms.experiment_evaluation`` module.
"""
from app.algorithms.experiment_evaluation import *  # noqa: F401, F403
