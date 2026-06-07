"""
Rule auto-discovery via importlib.
Scans a package for BaseRule subclasses and instantiates them.
"""
import importlib
import importlib.util
import inspect
import pkgutil
from pathlib import Path
from typing import List, Type

from src.engine.base import BaseRule


def discover_rules(package_name: str = "src.domains") -> List[BaseRule]:
    """
    Auto-discover all concrete BaseRule subclasses in a package.

    Walks every module in the package, finds classes that inherit
    BaseRule, instantiates them, and returns the list.

    Usage:
        rules = discover_rules("src.domains")
        # rules contains instances of all concrete rule classes
    """
    discovered: List[BaseRule] = []

    try:
        package = importlib.import_module(package_name)
    except ImportError:
        return discovered

    # Walk all subpackages and modules
    for _, module_name, is_pkg in pkgutil.walk_packages(
        package.__path__, package.__name__ + "."
    ):
        if is_pkg:
            continue  # skip packages, find modules

        try:
            module = importlib.import_module(module_name)
        except Exception:
            continue  # broken module? skip it

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, BaseRule)
                and obj is not BaseRule
                and not getattr(obj, "__abstractmethods__", None)
            ):
                try:
                    instance = obj()
                    discovered.append(instance)
                except Exception:
                    continue  # broken rule? skip it

    # Sort by rule_id for deterministic ordering
    discovered.sort(key=lambda r: r.rule_id)
    return discovered
