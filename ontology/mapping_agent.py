"""
Facade adapter for backward compatibility with existing mapping calls.
Forwards mapping_agent calls to systems.generator.ontology_mapping.mapping_agent.
"""
from systems.generator.ontology_mapping.mapping_agent import (
    map_column,
    map_all_sources,
    load_catalog_nodes,
    build_system_prompt,
    MAPPING_CACHE_PATH,
)

__all__ = [
    "map_column",
    "map_all_sources",
    "load_catalog_nodes",
    "build_system_prompt",
    "MAPPING_CACHE_PATH",
]
