"""
Facade adapter for backward compatibility with existing feature builder calls.
Forwards calls to systems.generator.feature.builder.
"""
from systems.generator.feature.builder import (
    load_catalog,
    build_features,
    save_features_npy,
    load_features_npy,
)

__all__ = [
    "load_catalog",
    "build_features",
    "save_features_npy",
    "load_features_npy",
]
