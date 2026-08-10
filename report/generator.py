"""
Facade adapter for backward compatibility with existing tests and callers.
Forwards generate_report calls to systems.backend.app.report.generator.
"""
from systems.backend.app.report.generator import (
    generate_report,
    ASSET_TYPE_LABELS,
    STATUS_GRADE_LABELS,
    STATUS_SENTENCES,
    FEATURE_DISPLAY_LABELS,
    SENSOR_DISPLAY_LABELS,
    INSPECTION_CHECK_LABELS,
    INSPECTION_PLAIN_REASONS,
    INSPECTION_REQUEST_LIMITATIONS,
    STATUS_SUMMARY_LIMITATIONS,
)

__all__ = [
    "generate_report",
    "ASSET_TYPE_LABELS",
    "STATUS_GRADE_LABELS",
    "STATUS_SENTENCES",
    "FEATURE_DISPLAY_LABELS",
    "SENSOR_DISPLAY_LABELS",
    "INSPECTION_CHECK_LABELS",
    "INSPECTION_PLAIN_REASONS",
    "INSPECTION_REQUEST_LIMITATIONS",
    "STATUS_SUMMARY_LIMITATIONS",
]
