"""Compatibility shim package — canonical source: ``app.algorithms``.

If both ``backend/`` and ``backend/app/`` are on ``sys.path`` the import
``from algorithms.X import Y`` resolves through this shim and ultimately
runs the code in ``backend/app/algorithms/X.py``.
"""
from app.algorithms import *  # noqa: F401, F403
