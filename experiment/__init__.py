"""
Specification Resistance in Machine Shopping Behaviour
=======================================================

Core experiment module. Tests whether frontier LLMs follow user purchase
specifications or override them with training-derived preferences.

Design: 2 (Specification Type) x 6 (Precision Level) + mechanism isolation
        x 20 product categories x 3 assortments x 10 models x N trials
"""

from .conditions import CONDITION_REGISTRY, get_condition, list_conditions
from .runner import run_experiment, run_pilot, run_full

__all__ = [
    "CONDITION_REGISTRY",
    "get_condition",
    "list_conditions",
    "run_experiment",
    "run_pilot",
    "run_full",
]
